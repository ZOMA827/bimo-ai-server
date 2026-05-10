# 🤖 Bimo Pro: The Sentient AI Avatar 🚀

**Bimo Pro** is a cutting-edge interactive digital robot based on a **Multi-Agent System** architecture. It is designed to be an intelligent companion with self-awareness, dynamic emotions, and advanced capabilities in vision, hearing, and long-term memory.

## 🌟 Key Features

### 🧠 Multi-Brain Architecture
Bimo's intelligence is distributed across three specialized servers to ensure maximum speed and efficiency:
* **Chat Agent:** Handles lightning-fast conversations and long-form storytelling using **Llama-3.1-8b**.
* **Vision Agent:** Bimo's "eyes" that analyze images, clothing, and faces with high precision using advanced **Vision Models**.
* **Subconscious Agent:** Responsible for spontaneous initiative; Bimo doesn't just wait for commands—he starts talking if he senses your silence or boredom.

### 👁️ Advanced Senses
* **Real-Time Vision System:** Features a camera system that activates only when needed (e.g., when you say "Look") to analyze the environment, clothing, and facial expressions.
* **Smart Mic:** A microphone powered by a strict **State Machine** with automatic silence and noise detection to ensure a stable connection.
* **Face Tracking:** Bimo's eyes follow you wherever you move in the room using **Google ML Kit** technology.

### 🎭 Emotion & Personality Engine
* **Independent Personality (Ego):** Bimo has his own opinions; he laughs, gets sad, and feels shy or proud based on the context of the conversation.
* **Live Visual Interaction:** Features a mouth that moves in harmony with speech (**Lip-Sync**), automatic eye blinking, and tears that appear when he is sad.
* **Fluent Arabic Pronunciation:** Integrated with the **Mishkal** library for programmatic diacritics (Tashkeel) to ensure 100% correct Arabic pronunciation and clear articulation.

### 💾 Persistent Memory
* **Bimo Never Forgets:** Equipped with a memory engine that saves your name, interests, and relationship level, evolving his responses as your friendship grows.

## 🛠️ Tech Stack
* **Frontend:** Flutter (Dart) - Advanced UI/UX with complex animations.
* **Backend:** Python (Flask) - 3 connected microservices hosted on **Render**.
* **AI Models:** Groq Cloud (Llama 3.1, Llama Vision, Whisper Turbo).
* **Computer Vision:** Google ML Kit.

## 🏗️ Project Architecture
```text
Bimo_Pro/
├── mobile_app/ (Flutter)
│   ├── senses/ (Vision & Smart Mic)
│   ├── engines/ (Emotion Engine)
│   └── core/ (Multi-Server API Router)
└── backend_servers/ (Python/Flask)
    ├── chat_agent.py (The Voice)
    ├── vision_agent.py (The Eyes)
    └── subconscious_agent.py (The Ego)