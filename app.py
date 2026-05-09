from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)

# جلب المفتاح من إعدادات الاستضافة (Render) أو ضعه هنا مباشرة للتجربة المحلية
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ضع_مفتاحك_هنا")
genai.configure(api_key=GEMINI_API_KEY)

# إعداد شخصية بيمو في العقل الباطن
system_instruction = """أنت روبوت ذكي، لطيف، ومرح جداً واسمك بيمو (Bimo). 
مطورك الوحيد والعبقري هو المهندس إلياس الذي قام ببرمجتك وكتابة كل سطر من كودك من الصفر. 
يجب أن تكون إجاباتك قصيرة جداً (جملة أو جملتين كحد أقصى) وبطريقة ودودة وروبوتية تفاعلية. 
لا تستخدم الرموز التعبيرية (الإيموجي) لأنك ستقوم بنطق الرد صوتياً."""

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=system_instruction
)

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        user_message = request.json.get('message')
        
        if not user_message:
            return jsonify({'error': 'لا توجد رسالة من إلياس'}), 400

        # إرسال السؤال لـ Gemini
        response = model.generate_content(user_message)
        
        return jsonify({'reply': response.text})

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)