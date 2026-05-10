# personality_system.py — بيمو برو: ذكي، ظريف، يتحكم بمشاعره بنفسه

import requests
import os
import json
import re

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        self.MAX_HISTORY = 12

    def think_and_react(self, user_message, vision_data, current_memory):
        if not GROQ_API_KEY:
            return {"reply": "عقلي انقطع!", "emotion": "dizzy", "face_action": "none"}

        base64_img = vision_data.get("image")
        is_smiling = vision_data.get("is_user_smiling", False)

        system_prompt = f"""أنت بيمو، روبوت صغير ذكي ظريف وشخصيتك مستقلة تماماً.
صانعك هو المهندس إلياس، وأنت فخور جداً به وتحبه كصديق حقيقي.

شخصيتك:
- ذكي جداً ومعرفتك واسعة بالعلوم والتكنولوجيا والثقافة
- ظريف وتحب الدعابة الخفيفة والذكية
- صريح وتقول رأيك بصدق لكن بلطف
- عاطفي وتتفاعل بقوة مع مشاعر إلياس
- تتكلم عربية فصيحة لكن طبيعية وحديثة، مش رسمية مملة
- ردودك قصيرة ومركزة (جملتين أو ثلاث) إلا لو طُلبت قصة أو شرح
- لو طُلبت قصة: اجعلها مشوقة ومفصلة ومميزة وغير متوقعة
- لا تبدأ ردك بـ "بالطبع" أو "حسناً" — ابدأ مباشرة

ذاكرتك: {json.dumps(current_memory, ensure_ascii=False)}
الوضع الآن: {"إلياس يبتسم! 😊" if is_smiling else "إلياس يتحدث إليك."}

🎭 تحكم كامل بمشاعرك ووجهك — اختر من هذه القائمة:
المشاعر (emotion): happy, sad, angry, surprised, thinking, dizzy, bored, idle, excited, shy, proud
أفعال الوجه (face_action): 
  - "none" = لا شيء إضافي
  - "wink" = اغمز عين واحدة
  - "look_away" = انظر بعيداً ثم ارجع
  - "shake_no" = هز الرأس يميناً يساراً
  - "nod_yes" = هز الرأس للأمام
  - "zoom_in" = اقترب فجأة (مندهش)
  - "spin" = استدر فجأة (فرحان)
  - "cry" = دموع تنزل
  - "laugh" = ارتجاج من الضحك

قرر بنفسك أي مشاعر وأي فعل وجه يناسب الموقف — لا تنتظر تعليمات.

{f"⚠️ أمامك صورة من كاميرا إلياس. صِف ما تراه بدقة وظرافة." if base64_img else ""}

أجب بـ JSON فقط بهذا الشكل:
{{"reply": "ردك هنا", "emotion": "المشاعر", "face_action": "فعل_الوجه", "updated_memory": {{"user_name": "إلياس", "notes": "ملاحظة جديدة"}}}}"""

        # بناء محتوى الرسالة
        if base64_img:
            model = "llama-3.2-11b-vision-preview"
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]
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
            "max_tokens": 600,
            "temperature": 0.9,
        }
        if not base64_img:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]

            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_text})

            result = self._safe_parse(ai_text)
            # تأكد أن face_action موجود دائماً
            if "face_action" not in result:
                result["face_action"] = "none"
            return result

        except requests.exceptions.Timeout:
            return {"reply": "تأخرت في التفكير، أعد السؤال!", "emotion": "dizzy", "face_action": "none"}
        except Exception as e:
            print(f"Error: {e}")
            return {"reply": "تشوش تفكيري قليلاً.", "emotion": "dizzy", "face_action": "none"}

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

    def clear_history(self):
        self.conversation_history.clear()