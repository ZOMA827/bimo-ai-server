# app.py — إضافة: clear_history عند النوم + logging أفضل

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback

from memory_engine import MemoryEngine
from personality_system import PersonalitySystem

app = Flask(__name__)
CORS(app)

memory_engine = MemoryEngine()
personality_system = PersonalitySystem()

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        req_data = request.json
        if not req_data:
            return jsonify({'reply': 'ما وصلتني بيانات!', 'emotion': 'dizzy'}), 400

        user_message = req_data.get('message', '').strip()
        vision_data = req_data.get('vision', {})

        if not user_message:
            return jsonify({'reply': 'لم أسمع شيئاً.', 'emotion': 'idle'})

        print(f"📩 Message: {user_message} | Vision: {vision_data}")

        # 1. جلب الذاكرة
        current_memory = memory_engine.get_memory()

        # 2. التفكير والرد
        ai_response = personality_system.think_and_react(user_message, vision_data, current_memory)

        print(f"🤖 Response: {ai_response}")

        # 3. تحديث الذاكرة لو قرر
        if "updated_memory" in ai_response and isinstance(ai_response["updated_memory"], dict):
            memory_engine.save_memory(ai_response["updated_memory"])

        # ✅ 4. مسح التاريخ لو المستخدم قال ينام
        sleep_keywords = ["إلى اللقاء", "نوم", "أرتاح", "bye", "sleep"]
        if any(kw in user_message for kw in sleep_keywords):
            personality_system.clear_history()
            print("🌙 History cleared — going to sleep")

        return jsonify({
            'reply': ai_response.get('reply', 'حسناً'),
            'emotion': ai_response.get('emotion', 'idle'),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'reply': 'عذراً، لدي عطل فني في أعصابي.', 'emotion': 'dizzy'}), 500

@app.route('/health', methods=['GET'])
def health():
    """✅ endpoint للتحقق إن السيرفر شغال"""
    return jsonify({'status': 'ok', 'message': 'بيمو جاهز!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bimo server starting on port {port}")
    app.run(host='0.0.0.0', port=port)