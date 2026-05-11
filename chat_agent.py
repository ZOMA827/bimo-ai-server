# chat_agent.py — الفص الأول: وكيل الحوار السريع
# ✅ تم التحديث إلى Llama 3.1 8B Instant لتفادي قيود السيرفر المجانية (Error 429)

import os, json, re, requests

KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
# 🔥 التحديث السحري: هذا النموذج السريع يملك حدود استخدام ضخمة ولن يوقفك!
MODEL = "llama-3.1-8b-instant"

class ChatAgent:
    def __init__(self, memory):
        self.memory = memory
        self.history = []
        self.MAX_HISTORY = 6  # ذاكرة خفيفة لحماية السيرفر

    # ─────────────────────────────────────────
    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY:
            return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        is_smiling = vision_data.get("is_user_smiling", False)
        suppress_name = vision_data.get("suppress_name", False)

        system = self._build_prompt(mem, is_smiling, suppress_name)

        messages = [{"role": "system", "content": system}]
        for m in self.history[-self.MAX_HISTORY:]:
            messages.append(m)
        messages.append({"role": "user", "content": message})

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024, # مساحة ممتازة للقصص الطويلة
                "temperature": self._temperature(mem),
                "response_format": {"type": "json_object"},
            }, timeout=20)
            
            resp.raise_for_status() 
            
            ai_text = resp.json()["choices"][0]["message"]["content"]

            self.history.append({"role": "user",      "content": message})
            self.history.append({"role": "assistant",  "content": ai_text})

            result = self._parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", "idle")
            result["reply"] = self._clean_name(result.get("reply", ""), mem.get("user_name", ""))
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return self._err("تحدثنا كثيراً بسرعة! أعطني 10 ثوانٍ لألتقط أنفاسي.")
            return self._err(f"خطأ في سيرفر الذكاء الاصطناعي: {e.response.status_code}")
        except requests.Timeout:
            return self._err("تأخرت في التفكير، أعد السؤال!")
        except Exception as e:
            print(f"ChatAgent error: {e}")
            return self._err("تشوش تفكيري.")

    # ─────────────────────────────────────────
    def _build_prompt(self, mem: dict, is_smiling: bool, suppress_name: bool) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps(
            {k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")},
            ensure_ascii=False
        )
        rel = mem.get("relationship_level", 1)

        return f"""أنت بيمو — روبوت متطور يمتلك واجهة هولوغرام عائمة (HUD).
المستخدم: {name}
الذاكرة: {mem_str}

━━ شخصيتك وقواعد النطق ━━
• خاطبه دائماً كرجل (يا بطل، مستعد، إلخ).
• ⚠️ قاعدة النطق الذهبية: شكّل الكلمات العربية بالحركات بالكامل.

━━ 🌐 نظام الشاشات العائمة (HUD System) ━━
أنت تستطيع إظهار نوافذ هولوغرامية بجانبك!
1. إذا طلب المستخدم رؤية شيء (مثال: أرني لامبورغيني، صورة قطة، كيف يبدو إيفون 16):
   - اجعل "ui_action" = "show_image"
   - ضع في "media_url" هذا الرابط الحرفي: "https://image.pollinations.ai/prompt/{{THING}}" (استبدل {{THING}} باسم الشيء باللغة الإنجليزية بدون مسافات).
   - ضع في "media_title" وصفاً قصيراً للشيء.
2. إذا سأل عن أخبار أو طقس أو معلومات تحتاج مصدراً:
   - اجعل "ui_action" = "show_news"
   - ضع في "media_url" أي رابط حقيقي مفيد (مثال: https://www.google.com/search?q=طقس+اليوم).
   - ضع في "media_title" عنوان الخبر أو البحث.
3. إذا كان الحوار عادياً: اجعل "ui_action" = "none".

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك المُشكّل",
  "emotion": "happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh|sing",
  "ui_action": "none|show_image|show_news",
  "media_url": "رابط الصورة أو الخبر أو اتركه فارغاً",
  "media_title": "عنوان النافذة أو اتركه فارغاً",
  "updated_memory": {{}}
}}"""

    def _temperature(self, mem: dict) -> float:
        rel = mem.get("relationship_level", 1)
        return round(min(1.0, 0.7 + rel * 0.03), 2)

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text:
            return text
        parts = text.split(name)
        if len(parts) <= 2:
            return text  
        return (parts[0] + name + "".join(parts[2:])).replace("  ", " ").strip()

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}

    def clear_history(self):
        self.history.clear()