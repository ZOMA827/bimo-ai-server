# chat_agent.py — الفص الأول: J.A.R.V.I.S Architecture 🧠
# ✅ Tavily-First + Anti-429/400 Matrix + Strict JSON Forcing

import os, json, re, requests
import urllib.parse

# ─── مفاتيح API ───
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY") # نستخدمه فقط لليوتيوب الآن
TAVILY_API_KEY   = os.environ.get("TAVILY_API_KEY") # العقل الباحث الرئيسي

URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── مصفوفة النماذج المجانية (مضاد الانهيار) ───
# إذا تعطل الأول، يتدخل الثاني، ثم الثالث فوراً!
MODELS_MATRIX = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

# ─── صندوق الأدوات (مبسط لتفادي Error 400 مع النماذج الصغيرة) ───
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "استخدم هذه الأداة فوراً للبحث في الإنترنت عن معلومات حقيقية، أخبار، طقس، تحميل ألعاب أو برامج، أو صور.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "كلمات البحث الدقيقة"},
                    "need_image": {"type": "boolean", "description": "True إذا كان يطلب صورة أو تحميل"}
                },
                "required": ["query", "need_image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "استخدم هذه الأداة فوراً لتشغيل أو إحضار فيديو يوتيوب أو أغنية.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "اسم الفيديو"}},
                "required": ["query"]
            }
        }
    }
]

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 4 # للحفاظ على تركيز النماذج الصغيرة

    # 🔥 محرك الاتصال بـ Groq المقاوم للانهيار 429 و 400
    def _call_groq(self, messages, use_tools=False):
        for m in MODELS_MATRIX:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.3 if use_tools else 0.6, # حرارة منخفضة للأدوات لتجنب الهلوسة
                }
                
                # النماذج الصغيرة ترتبك من JSON Object + Tools في نفس الوقت
                if use_tools:
                    payload["tools"] = TOOLS
                    payload["tool_choice"] = "auto"
                else:
                    payload["response_format"] = {"type": "json_object"}
                
                resp = requests.post(URL, headers=self._headers(), json=payload, timeout=15)
                resp.raise_for_status()
                return resp.json()["choices"][0]
            except Exception as e:
                print(f"⚠️ Groq فشل في نموذج {m}: {e}")
                continue 
        return None

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GROQ_API_KEY: return self._err("مفتاح Groq مفقود في السيرفر!")

        mem = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة 1: التفكير واختيار الأداة ──
        choice = self._call_groq(messages, use_tools=True)
        if not choice:
            return self._err("أواجه ضغطاً هائلاً في سيرفراتي، جرب بعد ثوانٍ!")

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
                
                # 🔥 الإصلاح الجذري لـ Error 400 (تنسيق صارم يطلبه Groq)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result_data, ensure_ascii=False)
                })

            # تنظيف رسالة الذكاء لإعادة إرسالها (لتفادي Error 400)
            clean_ai_msg = {
                "role": "assistant",
                "content": ai_msg.get("content") or "",
                "tool_calls": ai_msg.get("tool_calls")
            }
            messages.append(clean_ai_msg)
            messages += tool_results
            
            # توجيه إجباري لصياغة الـ JSON في الجولة الثانية
            messages.append({
                "role": "system", 
                "content": "لقد تلقيت نتائج الأداة الآن. يجب أن ترد بصيغة JSON فقط. إذا وجدت رابط media_url أو صورة، ضعها في الـ JSON واجعل ui_action يساوي show_card أو show_youtube."
            })

            # ── الجولة 2: صياغة الرد (JSON) ──
            final_choice = self._call_groq(messages, use_tools=False)
            if not final_choice:
                return self._err("جلبت المعلومات ولكن تعثرت في قراءتها.")
                
            result = self._parse(final_choice["message"].get("content", ""))

            # 🔥 حقن البيانات بالقوة لحماية الروبوت من النسيان
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
                    result["reply"] = "لقد أحضرت الفيديو يا بطل، تفضل!"

        else:
            # ── دردشة عادية ──
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...", "emotion": "happy", "face_action": "none"
            }

        # ── تجهيز الحقول النهائية ──
        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "حسناً."), name)

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result["reply"]})
        return result

    # ─── تنفيذ الأدوات ───
    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "tavily_search":
            return self._tavily_web_search(args.get("query", ""), args.get("need_image", False))
        if name == "youtube_search":
            return self._google_youtube_search(args.get("query", ""))
        return {}

    # 🌍 محرك بحث Tavily (الدقيق والمصمم للذكاء الاصطناعي)
    def _tavily_web_search(self, query: str, need_image: bool) -> dict:
        print(f"🌍 Tavily Search: {query}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        if not TAVILY_API_KEY: return result

        try:
            fetch_images = need_image or any(w in query for w in ["صورة", "انمي", "لعبة", "تحميل"])
            payload = {
                "api_key": TAVILY_API_KEY, 
                "query": query, 
                "include_images": fetch_images, 
                "max_results": 2
            }
            res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
            
            if "results" in res and res["results"]:
                result["url"] = res["results"][0].get("url")
                result["title"] = res["results"][0].get("title")
                for item in res["results"]:
                    result["results"].append({"title": item.get("title"), "snippet": item.get("content")})
            
            if fetch_images and "images" in res and res["images"]:
                result["image_url"] = res["images"][0] # إحضار الصورة الحقيقية!
        except Exception as e:
            print(f"⚠️ خطأ تافيلي: {e}")

        return result

    # 🎬 محرك بحث يوتيوب (جوجل)
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

    # 🔥 البرومبت المعماري (System Prompt) لفرض السيطرة
    def _build_system(self, mem: dict) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت بيمو — روبوت ومساعد شخصي ذكي.
المستخدم: {name}
الذاكرة: {mem_str}

قواعد السيطرة الصارمة:
1. أنت ترد دائماً وأبداً بصيغة JSON حصراً.
2. إذا ألقى المستخدم التحية (مرحبا، كيف حالك) أو أراد الدردشة أو طلب قصة: إياك أن تستخدم أي أداة بحث! جاوب من خيالك كصديق.
3. إذا سأل المستخدم عن معلومة خارجية، طقس، تحميل لعبة، أنمي، أو طلب صورة: يجب عليك استخدام أداة (tavily_search) فوراً!
4. شكل الكلمات العربية بالحركات.

صيغة JSON المطلوبة منك:
{{
  "reply": "ردك الطبيعي بصوتك",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "الرابط إن وجد أو فارغ",
  "image_url": "رابط الصورة إن وجد أو فارغ",
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
    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none"}
    def clear_history(self): self.history.clear()