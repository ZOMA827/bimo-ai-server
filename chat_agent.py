# chat_agent.py — الفص الأول: 🧠 Gemini Brain Transplant
import os, json, re, requests, urllib.parse
import google.generativeai as genai

# ─── مفاتيح API ───
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def tavily_search(query: str, need_image: bool = False) -> dict:
    """ابحث في الإنترنت عن معلومات حقيقية، أخبار، طقس، تحميل ألعاب، أو صور."""
    print(f"🌍 Gemini طلب بحث Tavily: {query}")
    result = {"url": "", "image_url": "", "title": ""}
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

def youtube_search(query: str) -> dict:
    """استخدم هذا لتشغيل أو إحضار فيديو يوتيوب أو أغنية حصراً."""
    print(f"🎬 Gemini طلب بحث YouTube: {query}")
    if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
        res = requests.get(url, timeout=8).json()
        if "items" in res and len(res["items"]) > 0:
            return {"youtube_id": res["items"][0]["id"]["videoId"], "title": res["items"][0]["snippet"]["title"]}
    except Exception as e:
        print(f"⚠️ خطأ YouTube: {e}")
    return {"error": "لم أجد الفيديو."}

def take_photo() -> dict:
    """لتشغيل الكاميرا إذا طلب منك المستخدم أن تنظر إليه."""
    print("📸 Gemini طلب تشغيل الكاميرا")
    return {"camera_status": "opening_now", "note": "Tell the user you are looking at them."}

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.chat_session = None

    def _init_chat(self, system_instruction):
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
            tools=[tavily_search, youtube_search, take_photo],
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                response_mime_type="application/json" 
            )
        )
        self.chat_session = model.start_chat(enable_automatic_function_calling=True)

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GEMINI_API_KEY: return self._err("مفتاح Gemini مفقود في السيرفر!")

        mem = self.memory.get()
        system = self._build_system(mem)

        if not self.chat_session:
            self._init_chat(system)

        try:
            response = self.chat_session.send_message(message)
            text = response.text
        except Exception as e:
            print(f"⚠️ Gemini Error: {e}")
            return self._err("أعصابي مشدودة قليلاً، هل تعيد ما قلت؟")

        result = self._parse(text)

        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "حسناً."), name)

        print(f"🤖 بيمو (Gemini): {result['reply'][:80]}")
        return result

    def _build_system(self, mem: dict) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت بيمو — روبوت ذكي، مساعد، وصديق مرح جداً.
المستخدم: {name}
الذاكرة: {mem_str}

قواعد السيطرة العسكرية:
1. أنت ترد دائماً بصيغة JSON حصراً.
2. إذا قال المستخدم "مرحبا"، "كيف حالك"، أو طلب قصة: جاوب من خيالك كصديق ولا تستخدم أدوات البحث إطلاقاً!
3. استخدم أدوات البحث (tavily/youtube) فقط إذا سأل عن شيء يحتاج إنترنت أو وسائط.
4. إذا استخدمت أداة وحصلت على (url) أو (image_url) أو (youtube_id)، ضعها في الـ JSON واجعل (ui_action) إما show_card أو show_youtube.
5. إذا استخدمت أداة take_photo، اجعل (ui_action) يساوي take_photo لكي يعمل الهاتف.

صيغة JSON:
{{
  "reply": "ردك الطبيعي والودود المشكل بالحركات",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube|take_photo",
  "media_url": "الرابط أو youtube_id أو فارغ",
  "image_url": "رابط الصورة أو فارغ",
  "media_title": "العنوان أو فارغ",
  "updated_memory": {{}}
}}"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text or text.count(name) <= 1: return text
        idx = text.find(name)
        return (text[:idx+len(name)] + text[idx+len(name):].replace(name,"")).strip()

    def _parse(self, text: str) -> dict:
        try: return json.loads(text)
        except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none"}
    def clear_history(self): self.chat_session = None