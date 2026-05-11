# chat_agent.py — الفص الأول: بيمو كـ (Autonomous Agent) 🧠
# ✅ نظام مضاد للانهيار (Fallback) لمعالجة مشكلة Error 429 في Groq

import os, json, re, requests
import urllib.parse

# ─── مفاتيح API ───
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")

URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── صندوق الأدوات ───
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "ابحث في محرك Google عن أي معلومة، أخبار، طقس، أو روابط تحميل.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "جملة البحث الدقيقة في جوجل"},
                    "need_image": {"type": "boolean", "description": "True إذا كان يطلب صورة أو أنمي أو لعبة"}
                },
                "required": ["query", "need_image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "ابحث في YouTube لتشغيل فيديو أو أغنية.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "اسم الفيديو للبحث عنه"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_photo",
            "description": "لتشغيل الكاميرا عندما يطلب المستخدم منك رؤيته.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 8

    # 🔥 دالة مضادة للانهيار: تجرب النموذج الثقيل، ولو محظور تنقل للسريع فوراً
    def _call_groq(self, messages, use_tools=False):
        models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        for m in models:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.6,
                }
                if use_tools:
                    payload["tools"] = TOOLS
                    payload["tool_choice"] = "auto"
                else:
                    payload["response_format"] = {"type": "json_object"}
                
                resp = requests.post(URL, headers=self._headers(), json=payload, timeout=15)
                resp.raise_for_status()
                return resp.json()["choices"][0]
            except Exception as e:
                print(f"⚠️ Groq 429/فشل في نموذج {m}، جاري التبديل للموديل الاحتياطي... ({e})")
                continue 
        return None

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GROQ_API_KEY: return self._err("مفتاح Groq مفقود!")

        mem    = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة 1: بيمو يفكر بالدالة المضادة للانهيار ──
        choice = self._call_groq(messages, use_tools=True)
        if not choice:
            return self._err("أنا أواجه ضغطاً في التفكير، كرر طلبك يا بطل!")

        ai_msg = choice["message"]
        finish = choice.get("finish_reason", "")

        # ── إذا قرر استخدام أداة ──
        if finish == "tool_calls" or ai_msg.get("tool_calls"):
            tool_results = []
            fn_name = ""

            for call in ai_msg.get("tool_calls", []):
                fn_name = call["function"]["name"]
                fn_args = json.loads(call["function"]["arguments"] or "{}")
                print(f"🔧 بيمو يستخدم أداة: {fn_name}({fn_args})")

                if fn_name == "take_photo":
                    return {
                        "reply": "دعني ألقي نظرة...", "emotion": "thinking",
                        "face_action": "none", "ui_action": "take_photo",
                        "media_url": "", "image_url": "", "media_title": "", "updated_memory": {}
                    }

                result_data = self._execute_tool(fn_name, fn_args)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role":         "tool",
                    "name":         fn_name,
                    "content":      json.dumps(result_data, ensure_ascii=False)
                })

            messages.append(ai_msg)
            messages += tool_results
            messages.append({
                "role": "system", 
                "content": "استخدم البيانات التي عادت من الأدوات. إذا وجدت رابطاً أو صورة، أخبر المستخدم بصوتك أنك عرضتها له."
            })

            # ── الجولة 2: صياغة الرد بالدالة المضادة للانهيار ──
            final_choice = self._call_groq(messages, use_tools=False)
            if not final_choice:
                return self._err("بحثت ووجدت المعلومة، لكن تعثرت في إخبارك بها.")

            result = self._parse(final_choice["message"].get("content", ""))

            # فرض البيانات لتجنب الهلوسة
            for tr in tool_results:
                td = json.loads(tr["content"])
                
                if fn_name == "web_search":
                    if td.get("image_url"):
                        result["image_url"] = td["image_url"]
                        if result.get("ui_action") in ["none", "", None]: result["ui_action"] = "show_card"
                    if td.get("url"):
                        result["media_url"] = td["url"]
                        if result.get("ui_action") in ["none", "", None]: result["ui_action"] = "show_card"
                    if td.get("title") and not result.get("media_title"):
                        result["media_title"] = td["title"]

                if fn_name == "youtube_search" and td.get("youtube_id"):
                    result["media_url"]   = td["youtube_id"]
                    result["ui_action"]   = "show_youtube"
                    result["media_title"] = td.get("title", "يوتيوب 🎥")
                    if "لم أجد" in result.get("reply", ""):
                        result["reply"] = "لقد أحضرت لك الفيديو يا بطل، مشاهدة ممتعة!"

        else:
            # ── دردشة عادية ──
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...", "emotion": "idle", "face_action": "none", "ui_action": "none",
            }

        # ── إكمال الحقول ──
        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "..."), name)

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result.get("reply","")})
        return result

    # ─── التنفيذ الفعلي للأدوات ───
    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "web_search":
            return self._google_web_search(args.get("query", ""), args.get("need_image", False))
        if name == "youtube_search":
            return self._google_youtube_search(args.get("query", ""))
        return {}

    # 🌍 محرك بحث Google الرسمي
    def _google_web_search(self, query: str, need_image: bool) -> dict:
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID: return result
        try:
            url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&num=3"
            res = requests.get(url, timeout=10).json()
            if "items" in res:
                for item in res["items"]:
                    result["results"].append({"title": item.get("title"), "snippet": item.get("snippet")})
                result["url"] = res["items"][0].get("link")
                result["title"] = res["items"][0].get("title")

            if need_image or any(w in query for w in ["صورة", "انمي", "تحميل", "شكل", "لعبة"]):
                img_url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&searchType=image&num=1"
                img_res = requests.get(img_url, timeout=10).json()
                if "items" in img_res:
                    result["image_url"] = img_res["items"][0].get("link")
        except Exception as e:
            print(f"⚠️ Google Search error: {e}")
        return result

    # 🎬 محرك بحث YouTube Data API v3 الرسمي
    def _google_youtube_search(self, query: str) -> dict:
        if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
            res = requests.get(url, timeout=10).json()
            if "items" in res and len(res["items"]) > 0:
                return {"youtube_id": res["items"][0]["id"]["videoId"], "title": res["items"][0]["snippet"]["title"]}
        except Exception as e:
            print(f"⚠️ YouTube error: {e}")
        return {"error": "لم أجد الفيديو"}

    def _build_system(self, mem: dict) -> str:
        name    = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)
        return f"""أنت بيمو — صديق حقيقي.
المستخدم: {name}
الذاكرة: {mem_str}
شكّل الكلمات العربية دائماً.
المخرجات (JSON فقط):
{{
  "reply": "ردك",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "",
  "image_url": "",
  "media_title": "",
  "updated_memory": {{}}
}}"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text or text.count(name) <= 1: return text
        idx = text.find(name)
        return (text[:idx+len(name)] + text[idx+len(name):].replace(name,"")).strip()

    def _parse(self, text: str) -> dict:
        try: return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _headers(self): return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none", "ui_action": "none"}
    def clear_history(self): self.history.clear()
