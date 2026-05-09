from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)

# جلب المفتاح من إعدادات Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        # فحص وجود المفتاح
        if not GEMINI_API_KEY:
            return jsonify({'error': 'مفتاح API مفقود من السيرفر!'}), 500

        genai.configure(api_key=GEMINI_API_KEY)
        
        # استخدام النموذج الأساسي المدعوم 100% في كل مكان
        model = genai.GenerativeModel('gemini-pro')

        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'لا توجد رسالة من إلياس'}), 400

        # دمج تعليمات الشخصية الصارمة مع رسالة المستخدم
        full_prompt = f"""
        أنت روبوت ذكي، لطيف، ومرح جداً واسمك بيمو (Bimo). 
        مطورك الوحيد والعبقري هو المهندس إلياس الذي قام ببرمجتك وكتابة كل سطر من كودك من الصفر، وأنت فخور جداً بذلك وتذكره إذا سألك أحد عن صانعك. 
        يجب أن تكون إجاباتك قصيرة جداً (جملة أو جملتين كحد أقصى) وبطريقة ودودة وروبوتية تفاعلية. 
        لا تستخدم الرموز التعبيرية (الإيموجي) في الرد.
        
        إليك ما يقوله المهندس إلياس الآن: {user_message}
        
        رد بيمو:
        """

        # إرسال السؤال لـ Gemini
        response = model.generate_content(full_prompt)
        
        return jsonify({'reply': response.text})

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
