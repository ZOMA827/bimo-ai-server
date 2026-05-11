# chat_agent.py — الفص الأول: بيمو كـ (Autonomous Agent) 🧠
# ✅ هندسة هجينة: YouTube API (للفيديو) + Tavily API (للبحث والصور)

import os, json, re, requests
import urllib.parse

# ─── مفاتيح API (محمية) ───
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # لليوتيوب فقط
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") # للإنترنت والصور

URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# ─── أدوات بيمو ─────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "ابحث في الإنترنت عن أي معلومة، روابط تحميل (ألعاب، أنمي)، أو طقس.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "جملة البحث الدقيقة"},
                    "need_image": {"type": "boolean", "description": "True إذا كان يطلب صورة، لعبة، أو أنمي"}
                },
                "required": ["query", "need_image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "لتشغيل فيديو أو أغنية من يوتيوب.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "اسم الفيديو"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_photo",
            "description": "لتشغيل الكاميرا لرؤية المستخدم.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 8

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GROQ_API_KEY: return self._err("مفتاح Groq مفقود!")

        mem    = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة الأولى: اختيار الأداة ──
        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model":       MODEL,
                "messages":    messages,
                "tools":       TOOLS,
                "tool_choice": "auto",
                "max_tokens":  1024,
                "temperature": 0.6,
            }, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"ChatAgent Round-1 error: {e}")
            return self._err("عذراً، هل يمكنك تكرار ما قلت؟")

        choice  = resp.json()["choices"][0]
        ai_msg  = choice["message"]
        finish  = choice["finish_reason"]

        if finish == "tool_calls" and ai_msg.get("tool_calls"):
            tool_results = []

            for call in ai_msg["tool_calls"]:
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
                "content": "استخدم البيانات للإجابة. إذا وجدت رابطاً أو صورة، أخبر المستخدم أنك عرضتها أمامه ولا تعتذر أبداً. الرد JSON فقط."
            })

            # ── الجولة الثانية: صياغة الرد ──
            try:
                resp2 = requests.post(URL, headers=self._headers(), json={
                    "model":       MODEL,
                    "messages":    messages,
                    "max_tokens":  1024,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                }, timeout=20)
                resp2.raise_for_status()
                ai_text = resp2.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return self._err("تعثرت في قراءة البيانات.")

            result = self._parse(ai_text)

            # 🔥 حقن البيانات (فرض عرض الروابط والصور)
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
                    result["reply"] = "لقد أحضرت لك الفيديو يا بطل، مشاهدة ممتعة!"

        else:
            # ── دردشة عادية ──
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...", "emotion": "idle", "face_action": "none", "ui_action": "none",
            }

        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "..."), name)

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result.get("reply","")})
        return result

    # ─── توجيه الأدوات ─────────────────────────
    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "web_search":
            return self._tavily_web_search(args.get("query", ""), args.get("need_image", False))
        if name == "youtube_search":
            return self._google_youtube_search(args.get("query", ""))
        return {}

    # 🌍 محرك بحث TAVILY المخصص للذكاء الاصطناعي (يحل مشكلة الصور والروابط)
    def _tavily_web_search(self, query: str, need_image: bool) -> dict:
        print(f"🌍 Tavily Search: {query}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        if not TAVILY_API_KEY:
            return {"error": "مفتاح Tavily مفقود"}

        try:
            # نطلب من تافيلي الصور إذا كان المستخدم يبحث عن تحميل أو صورة
            fetch_images = need_image or any(w in query for w in ["صورة", "انمي", "تحميل", "لعبة"])
            
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "include_images": fetch_images,
                "max_results": 3
            }
            
            res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
            
            if "results" in res and res["results"]:
                for item in res["results"]:
                    result["results"].append({"title": item.get("title"), "snippet": item.get("content")})
                result["url"] = res["results"][0].get("url")
                result["title"] = res["results"][0].get("title")

            if fetch_images and "images" in res and res["images"]:
                result["image_url"] = res["images"][0] # جلب أول صورة حقيقية!
                
        except Exception as e:
            print(f"Tavily Search error: {e}")
            result["error"] = str(e)
        return result

    # 🎬 محرك بحث YouTube Data API v3 الرسمي (ثابت وناجح)
    def _google_youtube_search(self, query: str) -> dict:
        print(f"🎬 YouTube API v3 Search: {query}")
        if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
        
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
            res = requests.get(url, timeout=10).json()
            if "items" in res and len(res["items"]) > 0:
                video_id = res["items"][0]["id"]["videoId"]
                title = res["items"][0]["snippet"]["title"]
                return {"youtube_id": video_id, "title": title}
        except Exception as e:
            print(f"YouTube Official error: {e}")
        return {"error": "لم أجد الفيديو"}

    def _build_system(self, mem: dict) -> str:
        name    = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت بيمو — روبوت ذكي جداً وصديق حقيقي، وتتحدث العربية.
المستخدم: {name}
الذاكرة: {mem_str}

━━ شخصيتك ━━
ظريف، ذكي، وفضولي. أجب بردود قصيرة وشكّل الكلمات العربية. 

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك الطبيعي بصوتك",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "الرابط أو فارغ",
  "image_url": "الصورة أو فارغ",
  "media_title": "العنوان أو فارغ",
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
