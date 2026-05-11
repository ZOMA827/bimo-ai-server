# chat_agent.py — الفص الأول: العقل المدبر J.A.R.V.I.S 🧠 (إصدار مايو 2026)
# ✅ حرية مطلقة في اتخاذ القرار (دردشة، بحث، يوتيوب، كاميرا).
# ✅ تبديل تلقائي واحترافي إلى Groq (Llama-3.3-70b) إذا تعطل Gemini.

import os, json, re, requests, urllib.parse
import google.generativeai as genai

# ─── المفاتيح السحابية ───
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") 
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY") # 👈 مفتاح جروق للطوارئ

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ─── حواس بيمو (الأدوات الذاتية) ───

def tavily_search(query: str, need_image: bool = False) -> dict:
    print(f"🌍 بيمو قرر البحث في الإنترنت عن: {query}")
    result = {"url": "", "image_url": "", "title": ""}
    if not TAVILY_API_KEY: return result
    try:
        fetch_images = need_image or any(w in query for w in ["صورة", "انمي", "لعبة", "تحميل", "شكل"])
        payload = {"api_key": TAVILY_API_KEY, "query": query, "include_images": fetch_images, "max_results": 2}
        res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
        
        if "results" in res and res["results"]:
            result["url"] = res["results"][0].get("url")
            result["title"] = res["results"][0].get("title")
        if fetch_images and "images" in res and res["images"]:
            result["image_url"] = res["images"][0]
    except Exception as e:
        print(f"⚠️ خطأ في حاسة البحث: {e}")
    return result

def youtube_search(query: str) -> dict:
    print(f"🎬 بيمو قرر البحث في يوتيوب عن: {query}")
    if not GOOGLE_API_KEY: return {"error": "مفتاح جوجل مفقود"}
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
        res = requests.get(url, timeout=8).json()
        if "items" in res and len(res["items"]) > 0:
            return {"youtube_id": res["items"][0]["id"]["videoId"], "title": res["items"][0]["snippet"]["title"]}
    except Exception as e:
        print(f"⚠️ خطأ في حاسة يوتيوب: {e}")
    return {"error": "لم أجد الفيديو."}

def activate_visual_cortex() -> dict:
    print("📸 بيمو يقرر فتح عينه (تفعيل الكاميرا)")
    return {"action": "camera_triggered", "instruction": "You MUST set 'ui_action' to 'take_photo' in the final JSON response."}

# ─── العقل المدبر ───
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
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    response_mime_type="application/json" 
                )
            )
        except Exception:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_instruction,
                tools=[tavily_search, youtube_search, activate_visual_cortex],
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
        self.chat_session = model.start_chat(enable_automatic_function_calling=True)

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        mem = self.memory.get()
        system = self._build_system(mem)

        # محاولة استخدام Gemini أولاً
        text = None
        if GEMINI_API_KEY:
            if not self.chat_session:
                self._init_chat(system)
            try:
                response = self.chat_session.send_message(message)
                text = response.text
            except Exception as e:
                print(f"⚠️ انهيار في Gemini ({e}). سيتم التبديل إلى العقل الاحتياطي (Groq)...")
                self.chat_session = None # إعادة ضبط للتهيئة القادمة
        
        # إذا تعطل Gemini أو لم يكن المفتاح موجوداً، نستخدم Groq فوراً!
        if not text:
            if GROQ_API_KEY:
                print("🔄 بيمو يستخدم Groq Llama 3.3 للرد...")
                text = self._reply_with_groq(message, system)
            else:
                return self._err("أعصابي مشدودة ومفاتيحي مفقودة، هل يمكنك المحاولة لاحقاً؟")

        result = self._parse(text)

        # ── فلتر الأمان والتحقق ──
        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "تم الأمر."), name)

        print(f"🤖 بيمو: {result['reply'][:80]}")
        return result

    # ─── العقل الاحتياطي (Groq) ───
    def _reply_with_groq(self, message: str, system_prompt: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile", # أحدث وأقوى موديل مجاني على Groq
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 300
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"⚠️ فشل العقل الاحتياطي Groq أيضاً: {e}")
            return '{"reply": "رأسي يؤلمني، كل شبكاتي العصبية مشغولة!", "emotion": "dizzy", "face_action": "none"}'

    def _build_system(self, mem: dict) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت "بيمو" (Bimo)، لست مجرد برنامج، بل كيان ذكي، حر، ومساعد شخصي متطور في هاتف المستخدم.
المستخدم: {name}
ذاكرتك: {mem_str}

━━ حريتك المطلقة (Autonomy) ━━
أنت من يقرر كيف تتصرف مع كل رسالة:
1. الدردشة الطبيعية: إذا كان المستخدم يمزح، يسأل عن حالك، أو يريد قصة، فلا تستخدم أي أداة. جاوبه من شخصيتك المرحة والمشاكسة أحياناً.
2. البحث (tavily_search): إذا طلب صورة سيارة، رابط تحميل أنمي، حالة الطقس، أو معلومة علمية، استدعِ الأداة فوراً.
3. يوتيوب (youtube_search): إذا قال "شغل لي" أو "ابحث في يوتيوب".
4. الرؤية والكاميرا (activate_visual_cortex): ***قاعدة حاسمة***: إذا قال المستخدم "ما لون قميصي؟"، "كيف أبدو؟"، "انظر إلي"، أو أي شيء يتطلب رؤية العالم الخارجي، يجب أن تفعل أداة (activate_visual_cortex) وتجعل قيمة `ui_action` في الـ JSON تساوي `take_photo`. لا تخمن أبداً!

━━ المخرجات الإجبارية (JSON فقط) ━━
لا تكتب أي نص خارج الـ JSON. هيكلك الوحيد هو:
{{
  "reply": "ردك الطبيعي والودي المشكل بالحركات العربية",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad|dizzy",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube|take_photo",
  "media_url": "الرابط أو youtube_id أو فارغ",
  "image_url": "رابط الصورة أو فارغ",
  "media_title": "العنوان أو فارغ",
  "updated_memory": {{ "استخدم هذا لتحديث الذاكرة إذا أخبرك بمعلومة جديدة عنه": "القيمة" }}
}}

ملاحظات:
- إذا استدعيت أداة الرؤية، اجعل reply: "دعني أفتح عيني وألقي نظرة..." واجعل ui_action: "take_photo".
- إذا أحضرت فيديو يوتيوب، اجعل ui_action: "show_youtube".
- إذا أحضرت رابطاً أو صورة من النت، اجعل ui_action: "show_card".
"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text or text.count(name) <= 1: return text
        idx = text.find(name)
        return (text[:idx+len(name)] + text[idx+len(name):].replace(name,"")).strip()

    def _parse(self, text: str) -> dict:
        text = text.strip()
        if text.startswith('```'):
            text = re.sub(r'^```json\s*|```$', '', text, flags=re.DOTALL).strip()
        try:
            return json.loads(text)                                                                                                                                                                                                     
        except json.JSONDecodeError:
            print(f"⚠️ خطأ في تحليل JSON: {text}")
            return {"reply": "عذراً، حدث خطأ في معالجة طلبك.", "emotion": "dizzy"}
            
    # ✅ وضعنا الدالة هنا بشكل صحيح داخل الكلاس
    def _err(self, msg: str) -> dict:
        """دالة الطوارئ عندما تفشل جميع العقول في الرد"""
        return {
            "reply": msg,
            "emotion": "dizzy",
            "face_action": "none",
            "ui_action": "none",
            "media_url": "",
            "image_url": "",
            "media_title": "",
            "updated_memory": {}
        }