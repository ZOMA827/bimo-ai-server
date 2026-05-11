# app.py — بيمو برو: ثلاثة فصوص + ذاكرة سحابية + فلتر هلوسات + نظام الهولوغرام

from flask import Flask, request, jsonify
from flask_cors import CORS
import os, traceback, threading, time, requests as req_lib

from memory_engine      import MemoryEngine
from chat_agent         import ChatAgent
from vision_agent       import VisionAgent
from subconscious_agent import SubconsciousAgent

app = Flask(__name__)
CORS(app)

SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# ─── الذاكرة والفصوص ───
memory       = MemoryEngine()
chat_agent   = ChatAgent(memory)
vision_agent = VisionAgent(memory)
subconscious = SubconsciousAgent(memory)

# ─── Keep-alive ───────────────────────────────
def _keep_alive():
    while True:
        time.sleep(590)
        if SELF_URL:
            try:
                req_lib.get(f"{SELF_URL}/health", timeout=8)
                print("💓 keep-alive OK")
            except Exception as e:
                print(f"💔 {e}")

if SELF_URL:
    threading.Thread(target=_keep_alive, daemon=True).start()

# ─── هلوسات Whisper المعروفة ─────────────────
WHISPER_HALLUCINATIONS = {
    "شكرا", "شكراً", "شكرا لكم", "شكراً لكم",
    "ترجمة", "ترجمة النص", "نانسي", "نانسي عجرم",
    "إلى اللقاء", "وداعاً", "وداعا",
    "thank you", "thanks", "bye", "goodbye",
    "subtitles", "subscribe",
}

def _is_hallucination(text: str) -> bool:
    t = text.strip().lower()
    if t in {h.lower() for h in WHISPER_HALLUCINATIONS}:
        return True
    if len(t) < 20:
        for h in WHISPER_HALLUCINATIONS:
            if h.lower() in t:
                return True
    return False

# ─── Routes ───────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/ask_bimo', methods=['POST'])
def ask_bimo():
    try:
        data        = request.json or {}
        message     = data.get('message', '').strip()
        vision_data = data.get('vision', {})

        if not message:
            return jsonify({'reply': 'لم أسمع شيئاً.', 'emotion': 'idle'})

        print(f"📩 {message}")
        image_b64 = vision_data.get('image')

        # ─── توجيه ذكي ───
        if image_b64:
            result = vision_agent.analyze(message, image_b64)
        else:
            result = chat_agent.reply(message, vision_data)

        # ─── حفظ الذاكرة ───
        updated = result.get('updated_memory', {})
        if updated and isinstance(updated, dict):
            memory.save(updated)

        # ─── تحديث مزاج + مؤقت العقل الباطن ───
        if result.get('emotion'):
            memory.add_mood(result['emotion'])
        subconscious.reset_idle_timer()

        # ─── نوم / مسح التاريخ ───
        sleep_kw = ["إلى اللقاء", "نوم", "أرتاح", "bye", "sleep", "مع السلامة"]
        if any(kw in message for kw in sleep_kw):
            chat_agent.clear_history()

        # 🔥 التحديث الجبار: السماح لأوامر الواجهة (الهولوغرام) بالمرور إلى الهاتف!
        return jsonify({
            'reply':       result.get('reply',       'حسناً'),
            'emotion':     result.get('emotion',     'idle'),
            'face_action': result.get('face_action', 'none'),
            'ui_action':   result.get('ui_action',   'none'),
            'media_url':   result.get('media_url',   ''),
            'media_title': result.get('media_title', ''),
        })

    except Exception:
        traceback.print_exc()
        return jsonify({'reply': 'عذراً، عندي عطل فني.', 'emotion': 'dizzy'}), 500

@app.route('/spontaneous', methods=['GET'])
def spontaneous():
    result = subconscious.get_spontaneous()
    if result:
        return jsonify(result)
    return jsonify({'speak': False})

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    try:
        key = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
        if not key:
            return jsonify({'error': 'GROQ_API_KEY مفقود'}), 500
        if 'file' not in request.files:
            return jsonify({'error': 'لا يوجد ملف'}), 400

        f = request.files['file']
        r = req_lib.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={'file': (f.filename, f.read(), f.content_type)},
            data={'model': 'whisper-large-v3-turbo', 'language': 'ar'},
            timeout=15,
        )
        r.raise_for_status()
        text = r.json().get('text', '').strip()

        if _is_hallucination(text):
            print(f"🚫 هلوسة Whisper تجاهلت: '{text}'")
            return jsonify({'text': ''})

        print(f"🎤 {text}")
        return jsonify({'text': text})

    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'فشل التحويل'}), 500

@app.route('/memory', methods=['GET'])
def get_memory():
    return jsonify(memory.get())

@app.route('/memory/reset', methods=['POST'])
def reset_memory():
    memory.reset()
    chat_agent.clear_history()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bimo → port {port}")
    app.run(host='0.0.0.0', port=port)