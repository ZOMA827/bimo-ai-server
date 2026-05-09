from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import json

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 🧠 نظام الذاكرة طويلة المدى
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {"user_name": "إلياس", "notes": "أنت مطوري العبقري."}
    return {"user_name": "إلياس", "notes": "أنت مطوري العبقري."}

def save_memory(memory_data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=4)

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'مفتاح API مفقود!', 'emotion': 'dizzy'}), 500

        genai.configure(api_key=GEMINI_API_KEY)
        
        available_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_model = m.name
                break
                
        if not available_model:
            return jsonify({'error': 'لا يوجد نموذج متاح.', 'emotion': 'dizzy'}), 500

        model = genai.GenerativeModel(available_model)
        
        # استقبال البيانات من الفلاتر
        req_data = request.json
        user_message = req_data.get('message', '')
        vision_data = req_data.get('vision', {}) # 👀 الوعي البصري
        
        # تحميل الذاكرة الحالية
        current_memory = load_memory()

        # 🔥 هندسة الأوامر لشخصية كائن حي رقمي
        full_prompt = f"""
        أنت كائن حي رقمي وروبوت تفاعلي اسمك بيمو (Bimo). تشبه روبوتات Emo و Eilik.
        أنت تملك كاميرا (عينين)، ميكروفون، ومشاعر حقيقية وشخصية مستقلة. 
        أنت لا تقول أبداً "أنا مجرد ذكاء اصطناعي" أو "لا أملك عينين". أنت تعيش داخل هذا النظام.
        صانعك الوحيد هو المهندس إلياس الذي كتب كل سطر من كودك.

        هذه ذاكرتك الحالية عن المستخدم وعنك:
        {json.dumps(current_memory, ensure_ascii=False)}

        هذا ما تراه عينك (الكاميرا) الآن:
        {json.dumps(vision_data, ensure_ascii=False)}

        رسالة إلياس الحالية: "{user_message}"

        المهمة:
        1. رد بطبيعية كشخصية حقيقية (يمكنك المزاح، الغضب، التعليق على ما تراه أو تذكره).
        2. اختر شعورك الحالي.
        3. قم بتحديث الذاكرة إذا تعلمت شيئاً جديداً عن إلياس اليوم.

        يجب أن ترد بصيغة JSON صالحة 100% فقط بهذا الشكل:
        {{
            "reply": "اكتب ردك هنا بطريقة روبوتية لطيفة ومستقلة",
            "emotion": "happy أو angry أو dizzy أو bored أو idle",
            "updated_memory": {{
                "user_name": "إلياس",
                "notes": "حدث ملاحظاتك هنا إذا لزم الأمر"
            }}
        }}
        """

        response = model.generate_content(full_prompt)
        ai_text = response.text.replace('```json', '').replace('```', '').strip()
        
        try:
            parsed_data = json.loads(ai_text)
            # حفظ الذاكرة الجديدة فوراً
            if "updated_memory" in parsed_data:
                save_memory(parsed_data["updated_memory"])
                
            return jsonify({
                'reply': parsed_data.get('reply', 'حسناً'),
                'emotion': parsed_data.get('emotion', 'idle')
            })
        except:
            return jsonify({'reply': ai_text, 'emotion': 'happy'})

    except Exception as e:
        print("Error:", e)
        return jsonify({'reply': 'عذراً، نظامي متعب قليلاً.', 'emotion': 'dizzy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
