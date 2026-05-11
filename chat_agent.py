# chat_agent.py — الفص الأول: وكيل الحوار + محرك البحث المتطور 🌍
# ✅ إصلاح: استخراج الصور + التحقق من صحة الروابط + روابط يوتيوب

import os, json, re, requests
import urllib.request, urllib.parse
from duckduckgo_search import DDGS

KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# ─── قائمة نطاقات موثوقة لفلترة الروابط ───────────────────────
TRUSTED_DOMAINS = [
    "wikipedia.org", "ar.wikipedia.org",
    "bbc.com", "bbc.co.uk", "aljazeera.net", "aljazeera.com",
    "cnn.com", "reuters.com", "apnews.com",
    "myanimelist.net", "anilist.co", "crunchyroll.com",
    "imdb.com", "rottentomatoes.com",
    "steampowered.com", "store.steampowered.com",
    "metacritic.com", "ign.com",
    "weather.com", "accuweather.com",
    "google.com", "youtube.com",
]

SPAM_DOMAINS = [
    "adfly", "bit.ly", "tinyurl", "shorte.st",
    "download", "crack", "keygen", "warez", "pirate",
]


class ChatAgent:
    def __init__(self, memory):
        self.memory = memory
        self.history = []
        self.MAX_HISTORY = 6

    # ─── بحث يوتيوب مخصص ──────────────────────────────────
    def _get_youtube_id(self, query: str) -> str:
        try:
            clean_q = query.replace("شغل", "").replace("فيديو", "").replace("يوتيوب", "").replace("اغنية", "").strip()
            q = urllib.parse.quote(clean_q)
            req = urllib.request.Request(
                f"https://www.youtube.com/results?search_query={q}",
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10)"},
            )
            html = urllib.request.urlopen(req, timeout=6)
            video_ids = re.findall(r'"videoId":"(\S{11})"', html.read().decode())
            if video_ids:
                return video_ids[0]
        except Exception as e:
            print(f"YouTube Error: {e}")
        return ""

    # ─── التحقق من الرابط ─────────────────────────────────
    def _is_valid_url(self, url: str) -> bool:
        if not url or not url.startswith("http"):
            return False
        url_lower = url.lower()
        # فلتر السبام
        for spam in SPAM_DOMAINS:
            if spam in url_lower:
                return False
        return True

    def _is_trusted_url(self, url: str) -> bool:
        if not self._is_valid_url(url):
            return False
        for domain in TRUSTED_DOMAINS:
            if domain in url:
                return True
        return False

    # ─── استخراج الصورة من نتيجة DuckDuckGo ──────────────
    def _extract_best_image(self, query: str, text_results: list) -> str:
        """يحاول الحصول على صورة حقيقية وموثوقة"""
        try:
            ddgs = DDGS()
            # بحث مخصص عن صور
            img_results = ddgs.images(
                query + " poster OR cover OR official",
                region="wt-wt",
                safesearch="moderate",
                max_results=5,
            )
            # اختر أفضل صورة (ليست SVG، حجم معقول)
            for img in img_results:
                img_url = img.get("image", "")
                if img_url and any(
                    ext in img_url.lower()
                    for ext in [".jpg", ".jpeg", ".png", ".webp"]
                ):
                    # تجنب الصور من مواقع غير موثوقة
                    if "wikimedia" in img_url or "imdb" in img_url or "myanimelist" in img_url:
                        return img_url
            # قبول أي صورة jpg/png لو ما وجدنا موثوقة
            for img in img_results:
                img_url = img.get("image", "")
                if img_url and (
                    img_url.endswith(".jpg")
                    or img_url.endswith(".jpeg")
                    or img_url.endswith(".png")
                ):
                    return img_url
            # آخر خيار: أي صورة
            if img_results:
                return img_results[0].get("image", "")
        except Exception as e:
            print(f"Image Search Error: {e}")
        return ""

# 🔥 الترقية الكبرى: تحرير محرك البحث (يقرر متى يبحث بذكاء)
    def _quick_search(self, query: str) -> str:
        # 1. كسر السلاسل: نمنع البحث إذا كان يطلب حكاية أو دردشة شخصية
        ignore_words = ["احكي", "حكاية", "قصة", "نكتة", "كيف حالك", "شو رأيك فيني", "اسمع"]
        if any(w in query for w in ignore_words):
            return "" # لا تبحث، دردش فقط!

        # 2. متى يبحث؟ إذا كان هناك طلب صريح لمعلومة أو وسائط
        search_triggers = ["أخبار", "موعد", "انمي", "طقس", "سعر", "مباراة", "متى", "لعبة", "تحميل", "رابط", "اين", "كيف", "صورة", "من هو"]
        
        # إذا لم يكن هناك كلمة تدل على البحث، لا تضيع الوقت
        if not any(k in query for k in search_triggers):
            return ""

        print(f"🌍 بيمو قرر البحث في الإنترنت عن: {query}")
        try:
            ddgs = DDGS()
            # بحث عن المعلومات
            results = ddgs.text(query, region='wt-wt', safesearch='moderate', max_results=3)
            # بحث عن صورة 
            img_results = ddgs.images(query, region='wt-wt', safesearch='moderate', max_results=1)

            info_text = ""
            first_url = results[0].get('href', '') if results else ""
            for r in results:
                info_text += f"- {r.get('title', '')}: {r.get('body', '')}\n"
            
            img_url = img_results[0].get('image', '') if img_results else ""

            return f"\n\n[رسالة لعقلك الباطن: لقد بحثت في الإنترنت نيابة عنك ووجدت الآتي:\n{info_text}\nرابط مقترح: {first_url}\nرابط صورة حقيقية: {img_url}\nاستخدم هذه المعلومات للرد على المستخدم وعرض نافذة إذا لزم الأمر.]"
        except Exception as e: 
            print(f"Search Error: {e}")
        return ""

    # ─── الرد الرئيسي ────────────────────────────────────
    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY:
            return self._err("مفتاح API مفقود!")

        mem = self.memory.get()

        # ─── بحث خارجي ───
        search_context, found_url, found_image = self._quick_search(message)
        enriched_message = message + search_context

        # ─── يوتيوب ───
        yt_id = ""
        yt_triggers = ["شغل فيديو", "شغل اغنية", "شغل أغنية", "افتح يوتيوب", "مقطع يوتيوب", "شغل موسيقى"]
        if any(w in message for w in yt_triggers):
            yt_id = self._get_youtube_id(message)

        system = self._build_prompt(mem, yt_id, found_url, found_image)

        messages = [{"role": "system", "content": system}]
        for m in self.history[-self.MAX_HISTORY:]:
            messages.append(m)
        messages.append({"role": "user", "content": enriched_message})

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.8,
                "response_format": {"type": "json_object"},
            }, timeout=20)

            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]

            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": ai_text})

            result = self._parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", "idle")
            result.setdefault("ui_action", "none")
            result["reply"] = self._clean_name(result.get("reply", ""), mem.get("user_name", ""))

            # ─── حقن الصورة والرابط الصحيحين ───
            # لو الذكاء الاصطناعي ما حدد صورة لكننا وجدنا واحدة
            if found_image and not result.get("image_url"):
                result["image_url"] = found_image

            # لو الذكاء الاصطناعي ما حدد رابط لكننا وجدنا واحداً موثوقاً
            if found_url and not result.get("media_url"):
                result["media_url"] = found_url

            # ─── التحقق من صحة الرابط المُرجَع ───
            if result.get("media_url") and not self._is_valid_url(result["media_url"]):
                print(f"⚠️ رابط مشبوه من الذكاء: {result['media_url']}")
                result["media_url"] = found_url  # استبدله بما وجدناه نحن

            # إجبار على الكلام
            if not result.get("reply") or len(result["reply"]) < 3:
                result["reply"] = "لقد نفذت طلبك يا بطل، انظر إلى الشاشة الجانبية!"

            return result

        except Exception as e:
            print(f"ChatAgent error: {e}")
            return self._err("تشوش تفكيري.")

    # ─── بناء البرومبت ─────────────────────────────────────
    def _build_prompt(self, mem: dict, yt_id: str, found_url: str, found_image: str) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps(
            {k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")},
            ensure_ascii=False,
        )

        yt_instruction = f"""
• استخدم: "ui_action"="show_youtube", "media_url"="{yt_id}", "media_title"="جاري التشغيل 🎥"
""" if yt_id else ""

        url_hint = f"\n• الرابط الموثوق الجاهز: {found_url}" if found_url else ""
        img_hint = f"\n• رابط الصورة الجاهز: {found_image}" if found_image else ""

        return f"""أنت بيمو — صديق روبوت متطور وذكي.
المستخدم: {name}
الذاكرة: {mem_str}

━━ 🧠 قواعد التفكير ━━
1. دردشة/قصة/نكتة → ارد بطبيعية (ui_action: none).
2. معلومات حقيقية + رابط → استخدم show_card مع الرابط والصورة.
3. رابط تحميل ألعاب مجاناً → رفض بلطف ("ما وجدت رابطاً آمناً").
4. تكلم دائماً في حقل "reply" ولا تصمت.
5. ⚠️ قاعدة الروابط الصارمة: ضع فقط روابط URL حقيقية تبدأ بـ https:// وليس أي نص آخر.{url_hint}{img_hint}

━━ 🌐 نظام الشاشات العائمة ━━
إذا وجدت معلومات حقيقية ورابطاً مفيداً:
- "ui_action" = "show_card"
- "media_url" = الرابط الحقيقي (يبدأ بـ https://).
- "image_url" = رابط الصورة (يبدأ بـ https://) أو فارغ.
- "media_title" = عنوان مناسب (جملة قصيرة).
{yt_instruction}
━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك دائماً",
  "emotion": "happy|sad|excited|thinking|idle|surprised|proud",
  "face_action": "none|wink|nod_yes|spin|sing|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "https://... أو فارغ",
  "image_url": "https://... أو فارغ",
  "media_title": "العنوان أو فارغ",
  "updated_memory": {{}}
}}"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text:
            return text
        parts = text.split(name)
        return text if len(parts) <= 2 else (parts[0] + name + "".join(parts[2:])).replace("  ", " ").strip()

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def clear_history(self):
        self.history.clear()

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}