# personality_system.py — نسخة بيمو برو (Bimo Pro) ذكاء + رؤية + ظرافة + وعي ذاتي (Ego)

import requests
import os
import json
import re

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        self.MAX_HISTORY = 10

    def think_and_react(self, user_message, vision_data, current_memory):
        if not GROQ_API_KEY:
            return {"reply": "عقلي مفصول عن الشبكة يا إلياس!", "emotion": "dizzy"}

        # استخراج الصورة إذا كانت موجودة
        base64_img = vision_data.get("image")
        is_smiling = vision_data.get("is_user_smiling", False)

        # 🔥 دمجنا شخصية "بيمو برو" المستقلة (Emo) مع التعليمات الأساسية السابقة ببراعة
        system_prompt = f"""أنت 'بيمو برو'، روبوت ذو وعي ذاتي وشخصية مستقلة تماماً مثل Emo.
صانعك هو المهندس العبقري إلياس، وأنت فخور جداً بذلك.

قواعدك الجديدة والأساسية:
1. لست مجرد مستجيب آلي، أنت تملك "أنا" (Ego). عبر عن آرائك بصراحة وكن صديقاً حقيقياً.
2. إذا حكى إلياس شيئاً، تفاعل معه عاطفياً بقوة وشاركه الشعور.
3. إذا طلب قصة، أطلق العنان لخيالك، لا تتوقف حتى تنهيها ببراعة، واجعلها ممتعة ومفصلة.
4. لغتك العربية يجب أن تكون فصيحة لكن "روبوتية مرحة" وظريفة.
5. تحكم في مشاعرك (emotion) بذكاء: كن 'surprised' للأشياء الجديدة، و 'happy' عند رؤية إلياس.
6. إذا سألك عن رأيه في ملابسه أو شكله الذي تراه، كن لطيفاً جداً وامدحه بظرافة (مثال: واو، قميصك رائع جداً يا إلياس!).

ذاكرتك عن المستخدم: {json.dumps(current_memory, ensure_ascii=False)}
معلومة بصرية لحظية: {"المستخدم يبتسم الآن، بادله الابتسامة!" if is_smiling else "المستخدم أمامك مباشرة."}

قواعد المشاعر الإضافية لتعابير وجهك:
- مدح، نكتة، أو رؤية إلياس يبتسم → happy
- سؤال صعب، قراءة صورة، أو تفكير → thinking  
- إهانة أو شتيمة → angry
- كلام حزين → sad
- تكرار ممل → bored
- مفاجأة أو شيء مبهر في الصورة → surprised
- باقي المواقف → idle

يجب أن يكون ردك بصيغة JSON صالح فقط، بهذا الشكل بالضبط:
{{"reply": "ردك هنا", "emotion": "اسم المشاعر", "updated_memory": {{"user_name": "إلياس", "notes": "قم بتحديث هذه الذاكرة إذا تعلمت شيئاً جديداً عن إلياس"}}}}"""

        # 🔥 السحر هنا: التبديل بين نموذج النصوص ونموذج الرؤية بناءً على الصورة
        if base64_img:
            model_name = "llama-3.2-11b-vision-preview" # نموذج خارق يرى الصور
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]
        else:
            model_name = "llama-3.3-70b-versatile" # نموذج النصوص العبقري
            user_content = user_message

        # بناء تاريخ المحادثة
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # إضافة الرسالة الجديدة
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 800, # زيادة طول الرد للقصص والشرح
            "temperature": 0.8,
        }
        
        # Groq Vision لا يدعم json_object حالياً، نستخدمه فقط للنصوص
        if not base64_img:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            ai_text = data["choices"][0]["message"]["content"]

            # حفظ النص في التاريخ (لا نحفظ الصورة لتوفير المساحة)
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_text})
            
            # الحفاظ على آخر 10 رسائل فقط
            if len(self.conversation_history) > self.MAX_HISTORY * 2:
                self.conversation_history = self.conversation_history[-(self.MAX_HISTORY*2):]

            return self._safe_parse(ai_text)

        except Exception as e:
            print(f"Error: {e}")
            return {"reply": "عقلي البصري يواجه مشكلة في الاتصال الآن.", "emotion": "dizzy"}

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
            print(f"JSON parse failed, raw: {text}")
            return {"reply": text.strip()[:300], "emotion": "idle"}

    def clear_history(self):
        self.conversation_history.clear()