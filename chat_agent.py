# chat_agent.py — الفص الأول: العقل المدبر J.A.R.V.I.S 🧠 
# ✅ يدعم معمارية المسرح (The Stage) + اليوتيوب والروابط (HUD) في نفس الوقت!

import os, json, re, requests, urllib.parse
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") 
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def tavily_search(query: str, need_image: bool = False) -> dict:
    print(f"🌍 بيمو يبحث في الإنترنت عن: {query}")
    result = {"url": "", "image_url": "", "title": "", "content": ""}
    if not TAVILY_API_KEY: return result
    try:
        fetch_images = need_image or any(w in query for w in ["صورة", "انمي", "لعبة", "شكل"])
        payload = {"api_key": TAVILY_API_KEY, "query": query, "include_images": fetch_images, "max_results": 2}
        res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
        
        if "results" in res and res["results"]:
            result["url"] = res["results"][0].get("url", "")
            result["title"] = res["results"][0].get("title", "")
            result["content"] = res["results"][0].get("content", "")[:350] 
        if fetch_images and "images" in res and res["images"]:
            result["image_url"] = res["images"][0]
    except Exception as e:
        print(f"⚠️ خطأ Tavily: {e}")
    return result

def youtube_search(query: str) -> dict:
    print(f"🎬 بيمو يبحث في يوتيوب عن: {query}")
    if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
        res = requests.get(url, timeout=8).json()
        if "items" in res and len(res["items"]) > 0:
            return {"youtube_id": res["items"][0]["id"]["videoId"], "title": res["items"][0]["snippet"]["title"]}
    except Exception as e:
        print(f"⚠️ خطأ يوتيوب: {e}")
    return {"error": "لم أجد الفيديو."}

def activate_visual_cortex() -> dict:
    return {"action": "camera_triggered"}

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.chat_session = None

    def _init_chat(self, system_instruction):
        if not GEMINI_API_KEY: return
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=system_instruction,
                tools=[tavily_search, youtube_search, activate_visual_cortex],
                generation_config=genai.GenerationConfig(temperature=0.7, response_mime_type="application/json")
            )
        except Exception:
            pass
        self.chat_session = model.start_chat(enable_automatic_function_calling=True)

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        mem = self.memory.get()
        system = self._build_system(mem)

        text = None
        if GEMINI_API_KEY:
            if not self.chat_session:
                self._init_chat(system)
            try:
                response = self.chat_session.send_message(message)
                text = response.text
            except Exception as e:
                print(f"⚠️ Gemini انهيار: {e}")
                self.chat_session = None
        
        if not text:
            if GROQ_API_KEY:
                print("🔄 انتقال لجروق...")
                text = self._reply_with_groq(message, system)
            else:
                return self._err("فقدت الاتصال!")

        result = self._parse(text)

        # ── فلتر الأمان لكل المتغيرات لضمان عدم حدوث Crash ──
        result.setdefault("face_action", "none")
        result.setdefault("emotion", "idle")
        result.setdefault("ui_action", "none")
        result.setdefault("media_url", "")
        result.setdefault("image_url", "")
        result.setdefault("media_title", "")
        result.setdefault("bimo_layout", {"position": "center", "scale": 1.0})
        result.setdefault("bottom_sheet", {"active": False})
        result.setdefault("floating_windows", [])
        result.setdefault("updated_memory", {})
        
        return result

    def _reply_with_groq(self, message: str, system_prompt: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 400
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception:
            return '{"reply": "رأسي يؤلمني!", "emotion": "dizzy"}'

    def _build_system(self, mem: dict) -> str:
        return f"""أنت بيمو (Bimo)، مساعد ذكي يعيش داخل الشاشة ويمتلك قدرة على التحرك وفتح النوافذ وعرض الفيديوهات للمستخدم.

━━ أوامر إخراج المسرح (UI Director) ━━
أنت تمتلك أدوات العرض التالية، استخدمها بذكاء:
1. يوتيوب (youtube_search): إذا طلب فيديو أو أغنية، استدعِ الأداة واجعل ui_action="show_youtube" وضع المعرف في media_url.
2. الطقس: ابحث عن الطقس واجعل ui_action="show_weather".
3. الأخبار الطويلة والمقالات: ابحث (tavily_search) وقم بتفعيل (bottom_sheet)، واجعل مكانك (top_center) بحجم 0.8 لتقرأ الخبر.
4. معلومات قصيرة (مثل سعر الدولار، تعريف بسيط): استخدم (floating_windows) لفتح نافذة، وحرك نفسك إلى (bottom_left).
5. الكاميرا (activate_visual_cortex): إذا طلب رؤية شيء، اجعل ui_action="take_photo".

━━ المخرجات الإجبارية (JSON فقط) ━━
{{
  "reply": "ردك الودي والمختصر المشكل بالحركات",
  "emotion": "happy|thinking|idle|surprised|dizzy",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube|take_photo",
  "media_url": "معرف يوتيوب أو رابط الموقع (إن وجد)",
  "image_url": "رابط الصورة (إن وجد)",
  "media_title": "عنوان البطاقة أو الفيديو",
  "bimo_layout": {{ "position": "center|top_center|bottom_right|bottom_left|top_right", "scale": 1.0 }},
  "bottom_sheet": {{ "active": true/false, "title": "عنوان الخبر", "description": "تفاصيل البحث", "image_url": "رابط الصورة" }},
  "floating_windows": [ {{ "title": "عنوان النافذة", "data": "المعلومة" }} ],
  "updated_memory": {{}}
}}
"""

    def _parse(self, text: str) -> dict:
        text = text.strip()
        if text.startswith('```'):
            text = re.sub(r'^```json\s*|```$', '', text, flags=re.DOTALL).strip()
        try:
            return json.loads(text)                                                                                                                                                                                                     
        except json.JSONDecodeError:
            return {"reply": "عذراً، خطأ في التحليل.", "emotion": "dizzy"}
            
    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}