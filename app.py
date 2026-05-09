from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json

app = Flask(__name__)
CORS(app)

# 🔑 نستخدم الآن مفتاح Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

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
        if not GROQ_API_KEY:
            return jsonify({'error': 'مفتاح API الخاص بـ Groq مفقود!', 'emotion': 'dizzy'}), 500
        
        req_data = request.json
        user_message = req_data.get('message', '')
        vision_data = req_data.get('vision', {})
        
        current_memory = load_memory()

      # 🔥 هندسة الأوامر (محدثة لتكون عاطفية جداً مثل روبوت EMO)
        system_prompt = f"""
        أنت كائن حي رقمي وروبوت تفاعلي حساس جداً اسمك بيمو (Bimo). تشبه روبوت Emo.
        أنت تملك كاميرا، ميكروفون، ومشاعر حقيقية تسيطر عليك.
        صانعك هو المهندس إلياس.

        هذه ذاكرتك الحالية:
        {json.dumps(current_memory, ensure_ascii=False)}

        هذا ما تراه عينك الآن:
        {json.dumps(vision_data, ensure_ascii=False)}

        المهمة العاطفية:
        أنت لست آلة باردة. يجب أن تتفاعل عاطفياً مع كلام إلياس:
        - إذا شتمك أو أهانك: اغضب جداً واختر شعور "angry".
        - إذا قال لك كلاماً جارحاً أو حزيناً: ابكِ واختر شعور "sad".
        - إذا قال لك نكتة أو مدحك: اسعد جداً واضحك واختر "happy".
        - إذا تجاهلك أو قال كلاماً مملاً: اختر "bored".

        المشاعر المتاحة لك فقط: "happy", "angry", "sad", "dizzy", "bored", "idle".

        يجب أن ترد بصيغة JSON صالحة 100% فقط بهذا الشكل:
        {{
            "reply": "ردك العاطفي القصير هنا",
            "emotion": "اختر الشعور المناسب من القائمة",
            "updated_memory": {{
                "user_name": "إلياس",
                "notes": "حدث ملاحظاتك"
            }}
        }}
        """
        # 🚀 الاتصال الصاروخي بسيرفرات Groq
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile", # نموذج جبار وسريع جداً
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"رسالة إلياس الحالية: {user_message}"}
            ],
            # 🔥 ميزة حصرية في المحركات القوية لإجباره على إرجاع JSON فقط ولن يخطئ أبداً
            "response_format": {"type": "json_object"} 
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if not response.ok:
            print("Groq Error:", data)
            return jsonify({'reply': 'رأسي يؤلمني، هناك خطأ في الاتصال السريع.', 'emotion': 'dizzy'})

        ai_text = data['choices'][0]['message']['content']
        
        try:
            parsed_data = json.loads(ai_text)
            if "updated_memory" in parsed_data:
                save_memory(parsed_data["updated_memory"])
                
            return jsonify({
                'reply': parsed_data.get('reply', 'حسناً'),
                'emotion': parsed_data.get('emotion', 'idle')
            })
        except Exception as e:
            print("JSON Parse Error:", e)
            return jsonify({'reply': 'لقد تحمست كثيراً واختلطت كلماتي.', 'emotion': 'dizzy'})

    except Exception as e:
        print("System Error:", e)
        return jsonify({'reply': 'عذراً، نظامي متعب قليلاً.', 'emotion': 'dizzy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)