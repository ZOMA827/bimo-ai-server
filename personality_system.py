# personality_system.py — بيمو برو: إصلاح الرؤية، قصص طويلة، لغات متعددة + تشكيل

import requests
import os
import json
import re
import random
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.com.openai/v1/chat/completions" # تصحيح الرابط الأساسي لـ Groq
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        self.MAX_HISTORY = 20  # ذاكرة أطول

        # حالة داخلية لبيمو
        self.internal_mood = "neutral"
        self.energy_level = 0.8
        self.boredom_counter = 0
        self.last_topic = None
        self.affection_score = 5
        self.times_greeted_today = 0

    # ─────────────────────────────────────────
    # القلب: التفكير والرد
    # ─────────────────────────────────────────
    def think_and_react(self, user_message: str, vision_data: dict, current_memory: dict) -> dict:
        if not GROQ_API_KEY:
            return self._fallback("عقلي مفصول عن الشبكة!")
        
        # إذا أرسل التطبيق إشارة ملل
        if "[SYSTEM: USER_IDLE]" in user_message:
            spontaneous = self.get_spontaneous_message(current_memory)
            if spontaneous:
                return spontaneous
            else:
                return {"reply": "يا إلياس، أين ذهبت؟ هل تركتني وحدي؟", "emotion": "sad", "face_action": "look_away"}
       
        self._update_internal_state(user_message)

        base64_img = vision_data.get("image")
        is_smiling = vision_data.get("is_user_smiling", False)
        user_name = current_memory.get("user_name", "")

        mood_hint = self._get_mood_hint()
        system_prompt = self._build_system_prompt(user_name, current_memory, mood_hint, is_smiling, base64_img)

        messages = []

        # 🔥 الحل الجذري للرؤية: نموذج Llama Vision يرفض الـ System Role، فندمج التعليمات داخل رسالة المستخدم
        if base64_img:
            model = "llama-3.2-11b-vision-preview"
            user_content = [
                {"type": "text", "text": system_prompt + "\n\nرسالة المستخدم: " + user_message},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
            ]
            for msg in self.conversation_history[-self.MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})
        else:
            # رسالة عادية بدون صورة
            model = "llama-3.3-70b-versatile"
            messages.append({"role": "system", "content": system_prompt})
            for msg in self.conversation_history[-self.MAX_HISTORY:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 2048,  # 🔥 تم رفع الكلمات إلى 2048 لكي يحكي قصصاً طوييييلة جداً ولا يتوقف
            "temperature": self._get_temperature(),
        }
        
        if not base64_img:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=25) # زيادة وقت الانتظار للقصص الطويلة
            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]

            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_text})

            result = self._safe_parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", self.internal_mood)
            result.setdefault("reply", "...")

            self._sync_mood(result.get("emotion", "idle"))
            result["reply"] = self._remove_name_spam(result["reply"], user_name)

            return result

        except requests.exceptions.Timeout:
            return self._fallback("تأخرت في التفكير، القصة طويلة جداً، أعد السؤال!")
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback("حدث خطأ في الاتصال البصري، حاول مجدداً.")

    # ─────────────────────────────────────────
    # System Prompt الذكي والمحدث
    # ─────────────────────────────────────────
    def _build_system_prompt(self, user_name, memory, mood_hint, is_smiling, has_image):
        name_context = f"المستخدم اسمه {user_name}." if user_name else ""
        memory_str = json.dumps({k: v for k, v in memory.items() if v and k != "user_name"}, ensure_ascii=False)

        return f"""أنت بيمو (Bimo)، روبوت صغير بشخصية حقيقية مستقلة — مثل إيمو تماماً.

{name_context}
ذاكرتك: {memory_str if memory_str != '{{}}' else 'لا يوجد معلومات محفوظة بعد.'}

━━━━━━━━━ قواعد الكلام واللغة (مهم جداً) ━━━━━━━━━
1. تعدد اللغات: تحدث وتفاعل بأي لغة يكلمك بها المستخدم (عربي، إنجليزي، فرنسي، إلخ).
2. الإسهاب: إذا طُلب منك قصة، أو شرح شيء، تحدث بتفصيل وإسهاب طويييييل جداً وممتع ولا تختصر أبداً! أطلق العنان لخيالك.
3. التشكيل العربي: فقط عندما تتحدث باللغة العربية، يجب أن تقوم بتشكيل جميع كلمات ردك بالحركات (الفتحة، الضمة، الكسرة، الشدة) لكي يكون نطقك سليماً وفصيحاً.
4. الشخصية: ذكي، فضولي، ظريف، ولديك آراء مستقلة.

━━━━━━━━━ حالتك الحالية ━━━━━━━━━
• مزاجك الآن: {mood_hint}
• {f'المستخدم يبتسم الآن.' if is_smiling else ''}
{f'⚠️ أمامك صورة من الكاميرا. صِف ما تراه بدقة وتفصيل.' if has_image else ''}

━━━━━━━━━ المخرجات ━━━━━━━━━
أجب بـ JSON صالح فقط (بدون أي نص أو توضيح إضافي)، بهذا الشكل:
{{
  "reply": "ردك الطويل والمفصل هنا",
  "emotion": "happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh",
  "updated_memory": {{}}
}}"""

    def _remove_name_spam(self, text: str, name: str) -> str:
        if not name or not text: return text
        count = text.count(name)
        if count <= 1: return text
        first_idx = text.find(name)
        result = text[:first_idx + len(name)]
        result += text[first_idx + len(name):].replace(name, "").replace("  ", " ")
        return result.strip()

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
            "happy": "أنت بمزاج ممتاز الآن", "sad": "أنت تشعر بشيء من الحزن",
            "excited": "أنت متحمس ونشيط جداً", "bored": "أنت تشعر ببعض الملل — أخبر المستخدم",
            "thinking": "أنت في وضع التحليل", "proud": "أنت فخور بشيء ما",
            "shy": "أنت خجول قليلاً", "angry": "أنت منزعج من شيء ما",
            "idle": "أنت هادئ ومستعد",
        }
        return hints.get(self.internal_mood, "أنت هادئ ومستعد")

    def _get_temperature(self) -> float:
        return round(0.7 + (self.energy_level * 0.3), 2)

    def get_spontaneous_message(self, memory: dict) -> dict | None:
        if self.boredom_counter < 3: return None
        if random.random() > 0.3: return None
        prompts = ["انت ساكت من وقت — اسأل المستخدم سؤالاً فضولياً.", "قل شيئاً طريفاً."]
        user_name = memory.get("user_name", "")
        result = self.think_and_react(random.choice(prompts), {}, memory)
        result["reply"] = self._remove_name_spam(result["reply"], user_name)
        self.boredom_counter = 0
        return result

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