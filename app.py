# app.py — نفس المنطق + keep-alive لمنع نوم Render المجاني

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
import threading
import time
import requests as req_lib

from memory_engine import MemoryEngine
from personality_system import PersonalitySystem

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

memory_engine = MemoryEngine()
personality_system = PersonalitySystem()

# ✅ Keep-alive: يصحي السيرفر كل 10 دقائق ليمنع نوم Render المجاني
def _keep_alive():
    while True:
        time.sleep(600)
        if SELF_URL:
            try:
                req_lib.get(f"{SELF_URL}/health", timeout=10)
                print("💓 keep-alive OK")
            except Exception as e:
                print(f"💔 keep-alive failed: {e}")

if SELF_URL:
    threading.Thread(target=_keep_alive, daemon=True).start()
    print(f"💓 Keep-alive started → {SELF_URL}")
else:
    print("⚠️ RENDER_EXTERNAL_URL غير مضبوطة — keep-alive معطل")

# ────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ────────────────────────────────────────────
@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        req_data = request.json
        if not req_data:
            return jsonify({'reply': 'ما وصلتني بيانات!', 'emotion': 'dizzy'}), 400

        user_message = req_data.get('message', '').strip()
        vision_data  = req_data.get('vision', {})

        if not user_message:
            return jsonify({'reply': 'لم أسمع شيئاً.', 'emotion': 'idle'})

        print(f"📩 {user_message}")

        current_memory = memory_engine.get_memory()
        ai_response    = personality_system.think_and_react(
            user_message, vision_data, current_memory
        )

        print(f"🤖 {ai_response}")

        if "updated_memory" in ai_response and isinstance(ai_response["updated_memory"], dict):
            memory_engine.save_memory(ai_response["updated_memory"])

        sleep_kw = ["إلى اللقاء", "نوم", "أرتاح", "bye", "sleep"]
        if any(kw in user_message for kw in sleep_kw):
            personality_system.clear_history()
            print("🌙 history cleared")

        return jsonify({
            'reply':   ai_response.get('reply',   'حسناً'),
            'emotion': ai_response.get('emotion', 'idle'),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'reply': 'عذراً، عندي عطل فني.', 'emotion': 'dizzy'}), 500

# ────────────────────────────────────────────
@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """تحويل الصوت إلى نص عبر Groq Whisper"""
    try:
        if not GROQ_API_KEY:
            return jsonify({'error': 'GROQ_API_KEY مفقود'}), 500

        if 'file' not in request.files:
            return jsonify({'error': 'لا يوجد ملف صوتي'}), 400

        f = request.files['file']
        url     = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files   = {'file': (f.filename, f.read(), f.content_type)}
        data    = {'model': 'whisper-large-v3-turbo', 'language': 'ar'}

        r = req_lib.post(url, headers=headers, files=files, data=data, timeout=15)
        r.raise_for_status()

        text = r.json().get('text', '').strip()
        print(f"🎤 Whisper: {text}")
        return jsonify({'text': text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bimo server → port {port}")
    app.run(host='0.0.0.0', port=port)