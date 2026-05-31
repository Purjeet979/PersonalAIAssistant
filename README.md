# Arjun AI Assistant 🤖

**Arjun** is a highly advanced, fully localized AI desktop assistant designed with a unique **Dual-Persona "Two-Brain" Architecture**. Unlike standard chatbots, Arjun can dynamically switch between a casual, empathetic companion and a precise, robotic task executor.

Built with **Python**, **Ollama (Local LLM)**, and **Tkinter**, this project features a custom **Reinforcement Learning from Human Feedback (RLHF)** system, allowing users to train and evolve the AI's behavior simply by clicking buttons in the GUI or giving voice ratings.

---

## 🌟 Key Innovations & Technology Stack

### 🧠 1. Dual-Persona "Two-Brain" System
We engineered a dynamic switching engine that changes the underlying AI model and voice settings based on context:
* **Arjun Mode (Friendly):** Uses a baseline `gemma:2b` model configured with a friendly, supportive Hinglish system prompt. Speaks naturally, uses Roman Hinglish, and acts as a close friend.
* **Jarvis Mode (Professional):** Uses `gemma:2b` configured with an Iron Man-style formal assistant prompt, starting replies with "Sir" and maintaining compose.
* **Dynamic Switching:** Switch instantly via voice (*"Switch to Jarvis"*) or by clicking the GUI mode button.

### 🗣️ 2. Natural Neural Speech (Microsoft Edge TTS)
Replaced traditional robotic speech with studio-quality neural voices:
* **Arjun Voice:** `hi-IN-MadhurNeural` (Natural Indian Hinglish male voice).
* **Jarvis Voice:** `en-GB-SoniaNeural` (Polished British English female voice).
* **Low-Latency Playback:** Uses ctypes to call the Windows Multimedia MCI API (`mciSendStringW`) directly to play MP3 audio, bypassing standard player overheads.
* **Offline Fallback:** Transparently falls back to SAPI5 offline speech (`pyttsx3`) if the network is down.

### ⚡ 3. Double-Buffered Pre-fetching Queue (TTS Streaming)
To eliminate latency from remote speech generation:
1. Splits response text into sentences using punctuation markers (`. ! ? |`).
2. Spawns a background thread that downloads individual sentence MP3 files concurrently.
3. The main thread pulls completed files from a queue and plays them instantly.
4. **Latency Reduction:** Starts speaking the first sentence in **under 100ms**, downloading subsequent sentences while the user is listening.

### 📂 4. Persistent Semantic Memory (ChromaDB Vector Store)
Replaced the simple text-file memory with a production-grade database:
* Uses a persistent **ChromaDB** client to store long-term user memories.
* Embeddings are generated dynamically using the local Ollama instance.
* Employs MD5 document hashing to ensure duplicate memories are rejected in $O(1)$ time.
* Semantic search uses cosine similarity with a matching threshold to prevent irrelevant context injection.

### 🎭 5. RLHF Self-Evolution System
A reinforcement learning feedback loop that logs ratings:
* **Interactive Dashboard:** Features **👍 Good** and **👎 Bad** buttons in the Tkinter window.
* **Voice Feedback:** Listens for verbal confirmations (e.g., *"Good job"*, *"Galat jawab"*) to rate responses.
* **Instant Logging:** Saves ratings in standard training format to a gold-standard dataset (`training/arjun_gold_data.jsonl`).
* **Self-Optimization:** Summarizes recent interaction logs to adjust system prompts dynamically on command.

### 🌐 6. Playwright Browser Automation (YouTube Autoplay)
* Automates video playback by launching a headful Chromium browser using **Playwright**.
* Extracts video search queries using Hinglish/English verb filters.
* Automatically selects and clicks the first video result in a background thread to prevent GUI freezing.

### 🛡️ 7. Resilience & Model Fallbacks
* **Model Fallbacks:** Checks local Ollama library models and falls back to active installed models dynamically if the preferred models (`gemma:2b` or `llama3:8b`) are missing.
* **Thread-Safety Lock:** Uses `threading.Lock` inside the audio manager to prevent audio collisions from concurrent events (e.g. alarms/timers firing while speaking).

### 🤖 8. Hybrid LLM Intent Router (Ollama JSON Mode)
* **Zero-Shot Classification:** Instead of relying purely on hardcoded if/else triggers, the system utilizes Ollama's Native JSON output mode to map complex, unscripted user queries to specific hardware/software actions.
* **Layered Architecture:** Maintains sub-millisecond response times for common commands while falling back to the intelligent LLM router for nuanced requests (like *"aankhein dukh rahi hai, light kam kar"*).

### 🎨 9. Modern CustomTkinter UI & Aesthetics
* **Dynamic Layouts:** Designed with `CustomTkinter` offering a transparent, borderless window with smooth curved edges and interactive dropdown toggle menus (`CTkOptionMenu`).
* **Sci-Fi Elements:** Clean floating widget aesthetic powered by transparent background rendering and responsive color themes.

---

## 🛠️ Full Feature List

### 🗣️ Voice & Interaction
* **Wake Word Detection:** Resumes from sleep on *"Hey Arjun"*, *"Hey Jarvis"*, or *"Wake up"*.
* **Continuous Conversation:** Remembers the last 20 turns of history.
* **Visual Dashboard:** Reactive eye animation indicating listening 🔵, thinking 🟡, and speaking 🟢.

### 💻 System & PC Control
* **Power Management:** Shutdown, Restart, and Sleep commands.
* **Hardware Controls:** Multi-step volume and screen brightness adjustments.
* **App Launcher:** Configurable custom applications (Notepad, Calculator, task manager, etc.).
* **Clipboard Reader:** Reads out copied clipboard text.

### 📝 Productivity & Memory
* **Note Taking:** *"Take a note"* / *"Read my notes"*.
* **File Search:** Deep scanning of local user folders (Downloads, Documents, Desktop) for requested filenames.
* **Gmail Integration:** Starred summaries, unread count reports, search, and email attachments alerts.
* **WhatsApp Automation:** Sends messages to saved contacts via web URL or App protocol.

---

## 📂 Project Structure

```text
JarvisAI/
├── main.py              # Entry point (Launches GUI + Assistant threads)
├── .gitignore           # Ignores database files, virtualenvs, models
├── requirements.txt     # Dependency list
├── custom_commands.json # Custom commands registry
├── jarvis/              # CORE SOURCE CODE
│   ├── ai_engine.py     # LLM Chat, Generate, and Self-Improvement logic
│   ├── assistant.py     # Voice command router and sleep loop
│   ├── audio.py         # Speech-to-Text and Thread-safe Neural TTS Queue
│   ├── features.py      # Playwright YouTube, weather, news, system control
│   ├── commands.py      # Custom command executor and process-closer
│   ├── gmail_tools.py   # Gmail API integration
│   ├── memory.py        # System prompt builder and MemoryState manager
│   ├── paths.py         # File paths and folder registers
│   ├── rewards.py       # RLHF reward feedback logger
│   └── vector_db.py     # ChromaDB vector store
├── model/               # Offline Vosk speech recognition files
├── training/            # RLHF gold training logs
└── logs/                # Session logs
```

---

## 🚀 Installation & Setup

### Prerequisites
* **Python 3.10+**
* **Ollama** installed and running

### 🛠️ Steps
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Initialize Playwright drivers:
   ```bash
   playwright install chromium
   ```
3. Run the assistant:
   ```bash
   python main.py
   ```

## Developed with ❤️ by Purjeet
