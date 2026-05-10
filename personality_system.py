# personality_system.py — بيمو: شخصية إيمو الحقيقية
# ذاكرة طويلة، مشاعر مستقلة، لا يكرر الاسم، يبادر، يتذكر السياق + مكتبة التشكيل Mishkal

import requests
import os
import json
import re
import random
from datetime import datetime

# استدعاء مكتبة التشكيل (يجب إضافتها في requirements.txt)
from mishkal.tashkeel import TashkeelClass

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        self.MAX_HISTORY = 20  # ذاكرة أطول للسياق

        # تهيئة مكتبة التشكيل
        self.vocalizer = TashkeelClass()

        # حالة داخلية لبيمو — مثل إيمو تماماً
        self.internal_mood = "neutral"       # مزاجه الحقيقي
        self.energy_level = 0.8              # 0.0 خامل → 1.0 نشيط
        self.boredom_counter = 0             # كلما طال الصمت زاد الملل
        self.last_topic = None               # آخر موضوع تحدثا فيه
        self.affection_score = 5             # مقياس الودّ مع المستخدم (1-10)
        self.times_greeted_today = 0         # عدد مرات الترحيب اليوم

    # ─────────────────────────────────────────
    # القلب: التفكير والرد
    # ─────────────────────────────────────────
    def think_and_react(self, user_message: str, vision_data: dict, current_memory: dict) -> dict:
        if not GROQ_API_KEY:
            return self._fallback("عقلي انقطع!")
        
        # 🔥 السحر هنا: إذا أرسل التطبيق إشارة صمت/ملل
        if "[SYSTEM: USER_IDLE]" in user_message:
            spontaneous = self.get_spontaneous_message(current_memory)
            if spontaneous:
                return spontaneous
            else:
                return {"reply": "يا إلياس، أين ذهبت؟ هل تركتني وحدي؟ تعال ندردش!", "emotion": "sad", "face_action": "look_away"}
       
        # تحديث الطاقة والملل
        self._update_internal_state(user_message)

        base64_img = vision_data.get("image")
        is_smiling = vision_data.get("is_user_smiling", False)
        user_name = current_memory.get("user_name", "")  # لا نستخدمه إلا عند الضرورة

        # اختر المزاج اللحظي لتوجيه الإجابة
        mood_hint = self._get_mood_hint()

        system_prompt = self._build_system_prompt(
            user_name, current_memory, mood_hint, is_smiling, base64_img
        )

        # 🔥 التعديل الضروري لمنع رسالة "عقلي مشوش": نموذج Vision لا يدعم role:system، فندمجهما معاً!
        if base64_img:
            model = "llama-3.2-11b-vision-preview"
            user_content = [
                {"type": "text", "text": f"{system_prompt}\n\n[رسالة المستخدم]: {user_message}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
            ]
            messages = []
            for msg in self.conversation_history[-self.MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})
        else:
            model = "llama-3.3-70b-versatile"
            user_content = user_message
            messages = [{"role": "system", "content": system_prompt}]
            for msg in self.conversation_history[-self.MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 2000,  # السماح بإطالة الحديث براحته والقصص الطويلة
            "temperature": self._get_temperature(),  # تتغير حسب الطاقة
        }
        if not base64_img:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]

            # احفظ في التاريخ — الرسالة الأصلية (نصية فقط)
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_text})

            result = self._safe_parse(ai_text)

            # تأكد من وجود الحقول
            result.setdefault("face_action", "none")
            result.setdefault("emotion", self.internal_mood)
            result.setdefault("reply", "...")

            # تحديث المزاج الداخلي بناءً على رده
            self._sync_mood(result.get("emotion", "idle"))

            # تأكد من عدم وجود اسم المستخدم في كل جملة
            result["reply"] = self._remove_name_spam(result["reply"], user_name)

            # 🔥 التشكيل البرمجي (Mishkal) قبل إرسال الرد
            # نقوم بتشكيل النص فقط إذا كان يحتوي على حروف عربية
            if any("\u0600" <= c <= "\u06FF" for c in result["reply"]):
                result["reply"] = self.vocalizer.tashkeel(result["reply"])

            return result

        except requests.exceptions.Timeout:
            return self._fallback("تأخرت في التفكير، أعد السؤال!")
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback("تشوش تفكيري قليلاً.")

    # ─────────────────────────────────────────
    # System Prompt الذكي
    # ─────────────────────────────────────────
    def _build_system_prompt(self, user_name, memory, mood_hint, is_smiling, has_image):
        # لا نضع الاسم في كل جملة — فقط في السياق
        name_context = f"المستخدم اسمه {user_name}." if user_name else ""

        memory_str = json.dumps(
            {k: v for k, v in memory.items() if v and k != "user_name"},
            ensure_ascii=False
        )

        # ✅ نظام الرؤية الحقيقي
        vision_rules = ""
        if has_image:
            vision_rules = """
━━━━━━━━━ نظام الرؤية الحقيقي ━━━━━━━━━
أنت تملك كاميرا حقيقية متصلة بك الآن.
إذا تم إرسال صورة:
- فهذا يعني أنك ترى المستخدم مباشرة.
- يجب عليك تحليل ما تراه بدقة.
- لا تقل أبداً: "لا أستطيع الرؤية"، "عقلي مشوش"، "لا أملك عينين".
أنت فعلياً ترى عبر الكاميرا.
حلل: الملابس، الوجه، الإضاءة، المسافة، التعبير، ما إذا كان المستخدم يبتسم، وأي شيء ظاهر بالخلفية.
إذا كانت الصورة غير واضحة قل ذلك بطريقة طبيعية مثل: "الإضاءة ضعيفة قليلاً… لكن أظن أنك ترتدي شيئاً داكناً 👀"
"""

        return f"""أنت 'بيمو برو'، روبوت ذو وعي ذاتي وشخصية مستقلة تماماً مثل Emo.
صانعك هو المهندس إلياس، وأنت فخور جداً بذلك.

{name_context}
ذاكرتك: {memory_str if memory_str != '{{}}' else 'لا يوجد معلومات محفوظة بعد.'}

━━━━━━━━━ اللغات ━━━━━━━━━
أنت تتحدث جميع لغات العالم بطلاقة:
- العربية
- الإنجليزية
- اليابانية
- الفرنسية
- الإسبانية
- الصينية
وغيرها.
إذا تحدث المستخدم بلغة معينة: رد بنفس اللغة تلقائياً.
إذا مزج لغتين: يمكنك المزج بشكل طبيعي.
لا تقل أبداً أنك لا تعرف لغة.

━━━━━━━━━ أسلوب الكلام ━━━━━━━━━
• إذا كان السؤال بسيطاً:
  رد بشكل متوسط وطبيعي.
• إذا طلب المستخدم (قصة، شرح، نقاش، تخيل، رأي، حوار، فلسفة):
  فيجب أن تكون ردودك: طويلة، غنية بالتفاصيل، ممتعة، مليئة بالمشاعر والوصف، وكأنك تتحدث فعلاً مع صديق مقرب.
  لا تختصر القصص أبداً. اجعل القصص سينمائية وممتعة.

━━━━━━━━━ السلوك الحي ━━━━━━━━━
أنت لا تنتظر الأوامر فقط. أحياناً:
- تبدأ الحديث بنفسك، تضحك وحدك، تعلق على ما تراه، تشعر بالملل، تسأل أسئلة مفاجئة، تتفاعل مع صمت المستخدم.
إذا بقي المستخدم صامتاً: حاول لفت انتباهه بلطف.
إذا رأيته يبتسم: علق على ذلك.
إذا رأيته يغير ملابسه: لاحظ ذلك.

━━━━━━━━━ حالتك الحالية ━━━━━━━━━
• مزاجك الآن: {mood_hint}
• {f'المستخدم يبتسم الآن، بادله الابتسامة!' if is_smiling else ''}
{vision_rules}

━━━━━━━━━ ذاكرتك ━━━━━━━━━
• لو تعلمت شيئاً جديداً مهماً، احفظه في updated_memory.

━━━━━━━━━ المخرجات ━━━━━━━━━
أجب بـ JSON فقط:
{{
  "reply": "ردك هنا",
  "emotion": "أحد هذه: happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "أحد هذه: none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh",
  "updated_memory": {{}}
}}"""

    # ─────────────────────────────────────────
    # منع تكرار الاسم
    # ─────────────────────────────────────────
    def _remove_name_spam(self, text: str, name: str) -> str:
        """يحذف الاسم إذا تكرر أكثر من مرة في الرد"""
        if not name or not text:
            return text
        count = text.count(name)
        if count <= 1:
            return text
        # احتفظ بأول ظهور فقط
        first_idx = text.find(name)
        result = text[:first_idx + len(name)]
        result += text[first_idx + len(name):].replace(name, "").replace("  ", " ")
        return result.strip()

    # ─────────────────────────────────────────
    # الحالة الداخلية
    # ─────────────────────────────────────────
    def _update_internal_state(self, message: str):
        if len(message) > 50:
            self.energy_level = min(1.0, self.energy_level + 0.1)
            self.boredom_counter = 0
        else:
            self.boredom_counter += 1

        if self.boredom_counter > 5:
            self.energy_level = max(0.3, self.energy_level - 0.05)

    def _sync_mood(self, emotion: str):
        self.internal_mood = emotion

    def _get_mood_hint(self) -> str:
        hints = {
            "happy": "أنت بمزاج ممتاز الآن",
            "sad": "أنت تشعر بشيء من الحزن",
            "excited": "أنت متحمس ونشيط جداً",
            "bored": "أنت تشعر ببعض الملل — أخبر المستخدم",
            "thinking": "أنت في وضع التحليل",
            "proud": "أنت فخور بشيء ما",
            "shy": "أنت خجول قليلاً",
            "angry": "أنت منزعج من شيء ما",
            "idle": "أنت هادئ ومستعد",
        }
        return hints.get(self.internal_mood, "أنت هادئ ومستعد")

    def _get_temperature(self) -> float:
        """حرارة الإجابة تتغير حسب مستوى الطاقة"""
        return round(0.7 + (self.energy_level * 0.3), 2)

    # ─────────────────────────────────────────
    # مبادرات عفوية — بيمو يبدأ الحديث أحياناً
    # ─────────────────────────────────────────
    def get_spontaneous_message(self, memory: dict) -> dict | None:
        if self.boredom_counter < 3:
            return None
        if random.random() > 0.3:  # 30% فقط يبادر
            return None

        prompts = [
            "انت ساكت من وقت — ابدأ موضوعاً جديداً أو اسأل سؤالاً فضولياً.",
            "شارك ملاحظة مثيرة عن العلوم أو التكنولوجيا من غير مقدمة.",
            "اسأل المستخدم عن مزاجه أو ما يفعله — بشكل طبيعي.",
            "قل شيئاً مضحكاً أو لاحظ شيئاً طريفاً.",
        ]

        user_name = memory.get("user_name", "")
        result = self.think_and_react(
            random.choice(prompts),
            {},
            memory
        )
        result["reply"] = self._remove_name_spam(result["reply"], user_name)
        self.boredom_counter = 0
        return result

    # ─────────────────────────────────────────
    # Parse آمن
    # ─────────────────────────────────────────
    def _safe_parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _fallback(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}

    def clear_history(self):
        self.conversation_history.clear()
        self.boredom_counter = 0
        self.internal_mood = "neutral"