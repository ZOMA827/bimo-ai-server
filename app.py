from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# استيراد الأنظمة التي صنعناها
from memory_engine import MemoryEngine
from personality_system import PersonalitySystem

app = Flask(__name__)
CORS(app)

# تشغيل المحركات في الخلفية
memory_engine = MemoryEngine()
personality_system = PersonalitySystem()

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        req_data = request.json
        user_message = req_data.get('message', '')
        vision_data = req_data.get('vision', {})

        # 1. جلب الذاكرة الحالية
        current_memory = memory_engine.get_memory()

        # 2. إرسال البيانات لنظام الشخصية ليفكر ويقرر
        ai_response = personality_system.think_and_react(user_message, vision_data, current_memory)

        # 3. تحديث الذاكرة إذا قرر الذكاء الاصطناعي ذلك
        if "updated_memory" in ai_response:
            memory_engine.save_memory(ai_response["updated_memory"])

        # 4. إرسال الرد النهائي لجسد بيمو (الفلاتر)
        return jsonify({
            'reply': ai_response.get('reply', 'حسناً'),
            'emotion': ai_response.get('emotion', 'idle')
        })

    except Exception as e:
        print("System Router Error:", e)
        return jsonify({'reply': 'عذراً، لدي عطل فني في أعصابي.', 'emotion': 'dizzy'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)