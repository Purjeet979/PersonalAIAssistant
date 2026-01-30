# Arjun AI Assistant 🤖

**Arjun** is a highly advanced, fully localized AI desktop assistant designed with a unique **Dual-Persona "Two-Brain" Architecture**. Unlike standard chatbots, Arjun can dynamically switch between a casual, empathetic companion and a precise, robotic task executor.

Built with **Python**, **Ollama (LLM)**, and **Tkinter**, this project features a custom **Reinforcement Learning from Human Feedback (RLHF)** system, allowing users to train and evolve the AI's behavior simply by clicking buttons in the GUI.

---

## 🌟 Key Innovations

### 🧠 1. Dual-Persona "Two-Brain" System
We engineered a dynamic switching engine that changes the underlying AI model and voice settings based on context:
* **Arjun Mode (Friendly):** Uses a fine-tuned `arjun-custom` model. It speaks naturally, uses slang, remembers context, and acts as a friend.
* **Jarvis Mode (Professional):** Uses the base `gemma:2b` model. It speaks formally, calls you "Sir," and focuses purely on efficient task execution.
* **Dynamic Switching:** Switch instantly via voice (*"Switch to Jarvis"*) or by clicking the GUI mode button.

### 📈 2. RLHF Self-Evolution System
A built-in feedback loop makes the AI smarter the more you use it:
* **GUI Feedback Buttons:** The dashboard features **👍 Good** and **👎 Bad** buttons.
* **Instant Data Capture:** Clicking a button (or saying *"Good job"*) instantly saves the last interaction into a "Gold Standard" dataset (`training/arjun_gold_data.jsonl`).
* **Self-Optimization:** The assistant includes an "Optimize Yourself" command that analyzes past error logs to update its own system prompt automatically.

### ⚡ 3. High-Performance Latency Optimization
To solve the common slowness of local LLMs, we implemented specific engineering fixes:
* **RAM Persistence:** The AI brain is forced to stay loaded in RAM for 60 minutes (`keep_alive="60m"`), making follow-up responses **instant**.
* **Audio Engine Caching:** The TTS engine initializes once at startup, eliminating the 1-second delay often found in Python speech libraries.
* **Optimized Search:** Wikipedia and web lookups are packet-limited to prevent network freezes during voice processing.

---

## 🛠️ Full Feature List

### 🗣️ Voice & Interaction
* **Wake Word Detection:** Always listening for "Hey Arjun" or "Wake up".
* **Continuous Conversation:** Intelligent history management (remembers the last 15 turns).
* **Visual Dashboard:** A reactive Tkinter GUI with eye animations that change color based on state (Listening 🔵, Thinking 🟡, Speaking 🟢).

### 💻 System & PC Control
* **Power Management:** Shutdown, Restart, and Sleep commands via voice.
* **Hardware Control:** Increase/Decrease Volume and Brightness.
* **App Launching:** Open specific apps or websites (Netflix, Notepad, YouTube, etc.).
* **Clipboard Reader:** Reads out text currently copied to your clipboard.

### 📝 Productivity & Memory
* **Long-Term Memory:** "Arjun, remember that my name is..." (Saves facts to disk).
* **Note Taking:** "Take a note" / "Read my notes".
* **File Search:** Scans the hard drive to find lost files.
* **Gmail Integration:** Summarizes inbox, searches emails, and alerts on new attachments.
* **WhatsApp Automation:** Send messages via voice.

### 🌐 Information & Media
* **Smart Search:** Wikipedia integration for general knowledge questions.
* **Weather:** Real-time weather reports.
* **News:** Reads the latest headlines.
* **Media Control:** Play/Pause music, Next/Previous track.

---

## 📂 Project Structure

The project follows a clean data architecture to separate source code from user data:

```text
JarvisAI/
├── main.py              # Entry point (Launches GUI + Assistant threads)
├── .gitignore           # Protects secrets & huge model files
├── requirements.txt     # Dependency list
├── jarvis/              # CORE SOURCE CODE
│   ├── ai_engine.py     # LLM Logic (Ollama + Memory + Persona Switching)
│   ├── assistant.py     # Main Event Loop & Voice Command Routing
│   ├── audio.py         # Text-to-Speech & Speech-to-Text Engine
│   ├── gui.py           # Tkinter Dashboard & Feedback Buttons
│   ├── rewards.py       # Logic for saving RLHF training data
│   ├── commands.py      # Custom command manager
│   ├── memory.py        # Long-term memory management
│   └── paths.py         # Centralized file path manager
├── model/               # Stores the .gguf AI models (Ignored by Git)
├── training/            # Stores "Gold" data from the Reward System
└── logs/                # Error logs (Auto-cleaned)

🚀 Installation & Setup
Prerequisites:

Python 3.10+

Ollama installed and running.

Install Dependencies:

Bash
pip install -r requirements.txt
Setup the Brain:

Download your fine-tuned arjun.gguf model (or use gemma:2b).

Place it in the model/ folder.

Run: ollama create arjun-custom -f Modelfile_Arjun

Run the Assistant:

Bash
python main.py
🤝 Future Roadmap
[ ] Integration of Flask for a Mobile Web Control Dashboard.

[ ] Vision capabilities (See and describe images).

[ ] Home Automation (IoT) control via local network.

Developed with ❤️ by Purjeet.

