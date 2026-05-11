# chat_agent.py — الفص الأول: J.A.R.V.I.S Architecture 🧠
# ✅ مجاني 100% | يستخدم YouTube API الرسمي + Tavily | مضاد للانهيار 429/400

import os, json, re, requests
import urllib.parse

# ─── مفاتيح API (تم التأكد من وجودها في Render) ───
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # هذا هو مفتاح YouTube الخاص بك!
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") # للبحث عن الروابط والصور

URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── مصفوفة النماذج المجانية (مضاد الانهيار) ───
# إذا تعطل الأول، يتدخل الثاني، ثم الثالث فوراً!
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

# ─── صندوق الأدوات (مبسط جداً للنماذج المجانية) ───
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "للبحث عن معلومات، أخبار، طقس، تحميل ألعاب أو صور.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "need_image": {"type": "boolean"}
                },
                "required": ["query", "need_image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "لتشغيل فيديو يوتيوب أو أغنية حصراً.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }
]

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 3 # ذاكرة قصيرة لمنع التسمم

    def _call_api(self, messages, use_tools=False):
        for m in MODELS:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.4 if use_tools else 0.7,
                }
                
                if use_tools:
                    payload["tools"] = TOOLS
                    payload["tool_choice"] = "auto"
                else:
                    payload["response_format"] = {"type": "json_object"}
                
                resp = requests.post(URL, headers=self._headers(), json=payload, timeout=15)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]
                print(f"⚠️ Groq {resp.status_code} في نموذج {m}")
            except Exception as e:
                print(f"⚠️ فشل الاتصال بنموذج {m}: {e}")
        return None

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GROQ_API_KEY: return self._err("مفتاح Groq مفقود!")

        mem = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة 1: بيمو يقرر (دردشة أم بحث؟) ──
        choice = self._call_api(messages, use_tools=True)
        if not choice:
            return self._err("أعصابي مشدودة قليلاً، هل تعيد ما قلت؟")

        ai_msg = choice["message"]
        finish = choice.get("finish_reason", "")

        # ── إذا قرر استخدام أداة ──
        if finish == "tool_calls" or ai_msg.get("tool_calls"):
            tool_results = []
            fn_name = ""
            
            for call in ai_msg.get("tool_calls", []):
                fn_name = call["function"]["name"]
                fn_args = json.loads(call["function"]["arguments"] or "{}")
                print(f"🔧 تشغيل أداة: {fn_name}({fn_args})")

                result_data = self._execute_tool(fn_name, fn_args)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result_data, ensure_ascii=False)
                })

            # تنظيف وتجهيز للجولة الثانية
            clean_ai_msg = {"role": "assistant", "content": "", "tool_calls": ai_msg.get("tool_calls")}
            messages.append(clean_ai_msg)
            messages += tool_results
            messages.append({
                "role": "system", 
                "content": "الآن صغ الرد النهائي بـ JSON. أخبر المستخدم أنك وجدت المطلوب وعرضته أمامه."
            })

            # ── الجولة 2: صياغة الرد بـ JSON ──
            final_choice = self._call_api(messages, use_tools=False)
            if not final_choice:
                return self._err("بحثت لكن تعثرت في النطق.")
                
            result = self._parse(final_choice["message"].get("content", ""))

            # حقن الروابط بالقوة لمنع الذكاء من إخفائها
            for tr in tool_results:
                td = json.loads(tr["content"])
                if fn_name == "tavily_search":
                    if td.get("image_url"): result["image_url"] = td["image_url"]
                    if td.get("url"): result["media_url"] = td["url"]
                    if td.get("title") and not result.get("media_title"): result["media_title"] = td["title"]
                    if result.get("media_url") or result.get("image_url"): result["ui_action"] = "show_card"

                if fn_name == "youtube_search" and td.get("youtube_id"):
                    result["media_url"] = td["youtube_id"]
                    result["ui_action"] = "show_youtube"
                    result["media_title"] = td.get("title", "يوتيوب 🎥")
                    result["reply"] = "لقد وجدت الفيديو، تفضل بالمشاهدة!"

        else:
            # ── دردشة عادية ──
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...", "emotion": "happy", "face_action": "none"
            }

        # ── تنظيف الحقول ──
        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "حسناً."), name)

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result["reply"]})
        return result

    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "tavily_search":
            return self._tavily_web_search(args.get("query", ""), args.get("need_image", False))
        if name == "youtube_search":
            return self._google_youtube_search(args.get("query", ""))
        return {}

    # 🌍 محرك بحث Tavily (قوي جداً للروابط والصور)
    def _tavily_web_search(self, query: str, need_image: bool) -> dict:
        print(f"🌍 Tavily Search: {query}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        if not TAVILY_API_KEY: return result

        try:
            fetch_images = need_image or any(w in query for w in ["صورة", "انمي", "لعبة", "تحميل"])
            payload = {"api_key": TAVILY_API_KEY, "query": query, "include_images": fetch_images, "max_results": 2}
            res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
            
            if "results" in res and res["results"]:
                result["url"] = res["results"][0].get("url")
                result["title"] = res["results"][0].get("title")
            if fetch_images and "images" in res and res["images"]:
                result["image_url"] = res["images"][0]
        except Exception as e:
            print(f"⚠️ خطأ تافيلي: {e}")
        return result

    # 🎬 محرك يوتيوب الرسمي (باستخدام مفتاح جوجل الخاص بك)
    def _google_youtube_search(self, query: str) -> dict:
        print(f"🎬 YouTube API: {query}")
        if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
        try:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
            res = requests.get(url, timeout=8).json()
            if "items" in res and len(res["items"]) > 0:
                return {"youtube_id": res["items"][0]["id"]["videoId"], "title": res["items"][0]["snippet"]["title"]}
        except Exception as e:
            print(f"⚠️ خطأ YouTube: {e}")
        return {"error": "لم أجد الفيديو."}

    def _build_system(self, mem: dict) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت بيمو — روبوت ذكي وصديق مرح.
المستخدم: {name}
الذاكرة: {mem_str}

قواعد السيطرة:
1. أنت ترد دائماً بصيغة JSON حصراً.
2. إذا قال المستخدم "مرحبا"، "كيف حالك"، أو طلب قصة/نكتة: إياك أن تستخدم أداة بحث! جاوب من خيالك.
3. استخدم البحث فقط وفقط إذا سأل عن شيء يحتاج إنترنت.

صيغة JSON:
{{
  "reply": "ردك الطبيعي",
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
        try: 
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _headers(self): return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none"}
    def clear_history(self): self.history.clear()