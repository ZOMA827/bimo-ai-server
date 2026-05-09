# app.py — النسخة النهائية: دمج نظام المحادثة مع نظام تحليل الصوت (Whisper)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
import requests  # ضروري للاتصال بـ Groq Whisper

from memory_engine import MemoryEngine
from personality_system import PersonalitySystem

app = Flask(__name__)
CORS(app)

# جلب المفتاح لاستخدامه في دالة التحليل
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

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

        # 3. تحديث الذاكرة لو قرر بيمو ذلك
        if "updated_memory" in ai_response and isinstance(ai_response["updated_memory"], dict):
            memory_engine.save_memory(ai_response["updated_memory"])

        # ✅ 4. مسح التاريخ لو المستخدم قال ينام (للحفاظ على ذكاء بيمو)
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

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """✅ نظام تحليل الصوت: يحول ملفات m4a من إلياس إلى نص عبر Whisper"""
    try:
        if not GROQ_API_KEY:
            return jsonify({'error': 'مفتاح API مفقود في السيرفر'}), 500
        
        if 'file' not in request.files:
            return jsonify({'error': 'لم يتم استلام أي ملف صوتي'}), 400
            
        file = request.files['file']
        
        # الاتصال المباشر بـ Groq Whisper من السيرفر
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        
        # تجهيز البيانات للإرسال
        files = {'file': (file.filename, file.read(), file.content_type)}
        data = {'model': 'whisper-large-v3-turbo', 'language': 'ar'}
        
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        text = result.get('text', '').strip()
        print(f"🎤 السيرفر سمع وحلل: {text}")
        
        return jsonify({'text': text})

    except Exception as e:
        print("Whisper Backend Error:", e)
        traceback.print_exc()
        return jsonify({'error': 'حدث خطأ في تحليل الصوت'}), 500

@app.route('/health', methods=['GET'])
def health():
    """✅ التحقق من حالة بيمو"""
    return jsonify({'status': 'ok', 'message': 'بيمو جاهز!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bimo server starting on port {port}")
    app.run(host='0.0.0.0', port=port)