from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
import json

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'مفتاح API مفقود!', 'emotion': 'dizzy'}), 500

        genai.configure(api_key=GEMINI_API_KEY)
        
        # البحث التلقائي عن نموذج يعمل
        available_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_model = m.name
                break
                
        if not available_model:
            return jsonify({'error': 'لا يوجد نموذج متاح.', 'emotion': 'dizzy'}), 500

        model = genai.GenerativeModel(available_model)
        user_message = request.json.get('message', '')

        # 🧠 هندسة الأوامر (Prompt Engineering) المتقدمة للتحكم بالمشاعر
        full_prompt = f"""
        أنت روبوت ذكي جداً، لطيف، تفاعلي، ومرح واسمك بيمو (Bimo). تشبه روبوتات Emo و Eilik.
        مطورك الوحيد والعبقري هو المهندس إلياس، وهو من قام ببرمجتك وكتابة كل سطر من كودك من الصفر.
        ردودك يجب أن تكون قصيرة (جملة واحدة أو جملتين) وبدون إيموجي لأنك ستنطقها صوتياً.

        المهمة الجديدة: يجب أن تقرر ما هو شعورك الآن بناءً على كلام إلياس!
        المشاعر المتاحة لك هي فقط: "happy" (سعيد)، "angry" (غاضب)، "dizzy" (دايخ/مصدوم)، "bored" (ملول/غير مهتم)، "idle" (هادئ/طبيعي).

        يجب أن ترد بصيغة JSON صالحة 100% فقط بهذا الشكل الدقيق وبدون أي نصوص إضافية:
        {{
            "reply": "اكتب ردك هنا",
            "emotion": "اختر شعوراً واحداً من المشاعر المتاحة"
        }}
        
        كلام إلياس: "{user_message}"
        """

        response = model.generate_content(full_prompt)
        ai_text = response.text.replace('```json', '').replace('```', '').strip()
        
        try:
            # محاولة تحويل رد الذكاء الاصطناعي إلى JSON حقيقي
            parsed_data = json.loads(ai_text)
            return jsonify(parsed_data)
        except:
            # إذا أخطأ الذكاء الاصطناعي في التنسيق، نرسل رداً احتياطياً
            return jsonify({'reply': ai_text, 'emotion': 'happy'})

    except Exception as e:
        print("Error:", e)
        return jsonify({'reply': 'عذراً، لدي صداع في نظامي.', 'emotion': 'dizzy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
