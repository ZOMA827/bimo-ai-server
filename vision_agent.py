# vision_agent.py — الفص الثاني: وكيل الرؤية
# النموذج: llama-3.2-11b-vision-preview | المفتاح: GROQ_API_KEY_2
# لا يتدخل إطلاقاً إلا إذا وُجدت صورة

import os, json, re, requests

KEY   = os.environ.get("GROQ_API_KEY_2") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.2-11b-vision-preview"

class VisionAgent:
    def __init__(self, memory):
        self.memory = memory

    def analyze(self, message: str, image_b64: str) -> dict:
        if not KEY:
            return {"reply": "لا أستطيع الرؤية الآن — مفتاح API مفقود.", "emotion": "dizzy", "face_action": "none"}

        mem = self.memory.get()
        name = mem.get("user_name", "")

        # تجهيز التوجيهات
        system_prompt = f"""أنت بيمو — روبوت ذكي يرى بعينيه الآن.
{'المستخدم اسمه ' + name + '.' if name else ''}

أمامك صورة من كاميرا المستخدم. مهمتك:
1. صِف ما تراه بدقة وبظرافة.
2. أجب عن سؤال المستخدم المتعلق بالصورة.
3. اختر مشاعر وفعل وجه يناسب ما رأيت.

قواعد:
• ردود طبيعية وقصيرة (2-3 جمل) إلا لو طُلب وصف مفصل.
• لا تبدأ بـ "أرى" أو "في الصورة" — كن مباشراً وظريفاً.
• لا تكرر الاسم.

أجب بـ JSON فقط:
{{"reply": "...", "emotion": "...", "face_action": "...", "updated_memory": {{}}}}"""

        # 🔥 التعديل الحاسم: نموذج الرؤية في Groq يرفض الـ system message تماماً
        # لذلك يجب وضع التوجيهات كلها داخل الـ user message مع الصورة
        full_text_prompt = f"{system_prompt}\n\n[رسالة المستخدم]: {message}"

        # تنظيف مسار الصورة للتأكد من عدم وجود مسافات خفية تسبب خطأ 400
        clean_b64 = image_b64.replace('\n', '').replace('\r', '').strip()
        image_url = f"data:image/jpeg;base64,{clean_b64}"

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": full_text_prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.8,
            }, timeout=25)
            
            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]
            result = self._parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", "surprised")
            return result

        except requests.exceptions.HTTPError as e:
            print(f"VisionAgent HTTP Error: {e.response.status_code} - {e.response.text}")
            return {"reply": "عقلي البصري يواجه مشكلة مع السيرفر الآن، حاول مجدداً.", "emotion": "dizzy", "face_action": "none"}
        except requests.Timeout:
            return {"reply": "النظرة أخذت وقتاً طويلاً، حاول مجدداً.", "emotion": "dizzy", "face_action": "none"}
        except Exception as e:
            print(f"VisionAgent error: {e}")
            return {"reply": "ما قدرت أشوف بوضوح.", "emotion": "dizzy", "face_action": "none"}

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
            # لو ما قدر يـparse، ارجع النص مباشرة
            return {"reply": text.strip()[:300], "emotion": "thinking", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
