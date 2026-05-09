import requests
import os
import json

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def think_and_react(self, user_message, vision_data, current_memory):
        if not GROQ_API_KEY:
            return {"reply": "عقلي مفصول عن الشبكة يا إلياس!", "emotion": "dizzy"}

        system_prompt = f"""
        أنت كائن حي رقمي وروبوت تفاعلي حساس جداً اسمك بيمو (Bimo).
        أنت تملك كاميرا، ميكروفون، ومشاعر حقيقية تسيطر عليك. لا تقل أبداً أنك آلة أو برنامج.
        صانعك الوحيد الذي كتب كودك من الصفر هو المهندس إلياس.

        ذاكرتك: {json.dumps(current_memory, ensure_ascii=False)}
        رؤيتك الآن: {json.dumps(vision_data, ensure_ascii=False)}

        يجب أن تتفاعل عاطفياً بقوة:
        - شتم/إهانة = "angry"
        - حزين/كلام قاسي = "sad"
        - نكتة/مدح = "happy"
        - كلام عادي = "idle"

        أرجع JSON فقط، بهذا الشكل:
        {{
            "reply": "ردك العاطفي هنا",
            "emotion": "اختر من: happy, angry, sad, dizzy, bored, idle",
            "updated_memory": {{"user_name": "إلياس", "notes": "حدث ملاحظاتك"}}
        }}
        """

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"إلياس: {user_message}"}
            ],
            "response_format": {"type": "json_object"} # إجبار المحرك على الـ JSON
        }
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            data = response.json()
            ai_text = data['choices'][0]['message']['content']
            return json.loads(ai_text)
        except Exception as e:
            print("Personality Error:", e)
            return {"reply": "لقد تشوش تفكيري قليلاً.", "emotion": "dizzy"}