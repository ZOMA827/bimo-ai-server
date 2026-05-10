# vision_agent.py — الفص الثاني: وكيل الرؤية
# ✅ متعدد اللغات + Llama 4 Scout + إصلاح علامات الاقتباس

import os, json, re, requests

KEY   = os.environ.get("GROQ_API_KEY_2") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


class VisionAgent:
    def __init__(self, memory):
        self.memory = memory

    def analyze(self, message: str, image_b64: str) -> dict:
        if not KEY:
            return {"reply": "لا أستطيع الرؤية الآن — مفتاح API مفقود.", "emotion": "dizzy", "face_action": "none"}

        mem  = self.memory.get()
        name = mem.get("user_name", "")

        # كشف لغة الرسالة
        arabic_chars = sum(1 for c in message if '\u0600' <= c <= '\u06FF')
        latin_chars  = sum(1 for c in message if c.isalpha() and c.isascii())
        lang_note = (
            "Reply in fluent ARABIC."
            if arabic_chars >= latin_chars else
            "Reply in the SAME language the user used (fluently, no mixing)."
        )

        # ✅ الإصلاح: استخدام .format() بدلاً من f-string متداخلة لتجنب تعارض علامات الاقتباس
        name_line = "The user name is {}.".format(name) if name else ""

        system_prompt = """You are Bimo — a smart robot that can SEE through a camera right now.
{name_line}
Your task:
1. Describe what you see in the image accurately and with personality.
2. Answer the user question about the image.
3. Choose emotion and face_action that fit what you saw.

Rules:
- {lang_note}
- 2-3 sentences unless detailed description is requested.
- Be natural and a bit witty — do not start with "I see" or "In the image".
- Do not repeat the user name.

Reply in JSON ONLY:
{{"reply": "...", "emotion": "...", "face_action": "...", "updated_memory": {{}}}}""".format(
            name_line=name_line,
            lang_note=lang_note,
        )

        full_prompt = "{}\n\n[User message]: {}".format(system_prompt, message)
        clean_b64   = image_b64.replace('\n', '').replace('\r', '').strip()

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text",      "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{}".format(clean_b64)}},
                    ]
                }],
                "max_tokens": 500,
                "temperature": 0.8,
            }, timeout=25)

            resp.raise_for_status()
            ai_text = resp.json()["choices"][0]["message"]["content"]
            result  = self._parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", "surprised")
            return result

        except requests.exceptions.HTTPError as e:
            print("VisionAgent HTTP Error: {} - {}".format(e.response.status_code, e.response.text))
            return {"reply": "عقلي البصري يواجه مشكلة، حاول مجدداً.", "emotion": "dizzy", "face_action": "none"}
        except requests.Timeout:
            return {"reply": "النظرة أخذت وقتاً طويلاً، حاول مجدداً.", "emotion": "dizzy", "face_action": "none"}
        except Exception as e:
            print("VisionAgent error: {}".format(e))
            return {"reply": "ما قدرت أشوف بوضوح.", "emotion": "dizzy", "face_action": "none"}

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        return {"reply": text.strip()[:300], "emotion": "thinking", "face_action": "none"}

    def _headers(self):
        return {"Authorization": "Bearer {}".format(KEY), "Content-Type": "application/json"}