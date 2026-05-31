# 🎭 Future Idea: Real-Time Face Emotion Detection

**Goal:** Integrate facial emotion recognition to make Arjun AI "emotion-aware", allowing it to change its response style based on the user's facial expressions (happy, sad, angry, neutral).

**Inspiration:** The existing `BiometricAuthDemo` project which already uses `faceExpressionNet`.

---

## 🏗️ Architecture & Approach (Zero-Lag & Privacy First)

Since Arjun AI is a desktop application, running continuous background face detection would cause significant lag and privacy concerns. The planned approach is **On-Demand Capture**.

### 🛡️ Privacy & Performance Mitigations:
1. **No Background Spying:** The webcam will NOT run constantly. It will only capture a single frame **when the user initiates a conversation** (e.g., says "Hey Arjun" or clicks the talk button).
2. **Hardware-Level Release:** The webcam is instantly released after capturing the frame, ensuring the camera LED turns off immediately.
3. **100% Local Processing:** Uses a lightweight Python library (`fer` or similar OpenCV-based models). No images are ever saved to disk or sent over the internet.
4. **Master Toggle:** A toggle in the GUI ("👁️ Vision Active: ON/OFF") will completely disable camera access when the user wants absolute privacy.

---

## 🛠️ Implementation Blueprint

When you are ready to implement this in the future, follow these steps:

### 1. Install Dependencies
Install the lightweight FER (Facial Expression Recognition) library and OpenCV:
```bash
pip install fer opencv-python tensorflow
```

### 2. Create `jarvis/emotion_detector.py`
Create a standalone module that handles the on-demand webcam capture and emotion processing:

```python
import cv2
from fer import FER

class EmotionDetector:
    def __init__(self):
        self.detector = FER(mtcnn=False) # Use Haar Cascade for speed
        
    def get_current_emotion(self):
        """Captures exactly ONE frame, detects emotion, and closes camera."""
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release() # Release immediately for privacy
        
        if not ret:
            return None
            
        emotions = self.detector.top_emotion(frame)
        if emotions and emotions[0]:
            emotion_name, score = emotions
            return {"emotion": emotion_name, "score": score}
        return None
```

### 3. Update AI Engine (`ai_engine.py`)
Modify the system prompt generation to inject the detected emotion:

```python
# Before sending the prompt to Ollama, check emotion:
emotion_data = emotion_detector.get_current_emotion()
if emotion_data:
    mood = emotion_data['emotion']
    system_prompt += f"\n[SYSTEM CONTEXT: The user currently looks {mood}. Adjust your tone to be empathetic and match this mood appropriately.]"
```

### 4. Update GUI (`window.py`)
Add a vision toggle button and a status label to show the last detected emotion.

```python
# Add to top status bar
self.vision_var = tk.BooleanVar(value=False)
vision_btn = ttk.Checkbutton(top_frame, text="👁️ Vision", variable=self.vision_var)
vision_btn.pack(side=tk.LEFT)

self.mood_label = tk.Label(top_frame, text="🎭 Mood: Unknown")
self.mood_label.pack(side=tk.LEFT, padx=10)
```

---

## 🚀 Potential Use Cases
- 😢 **Sad:** User looks sad → Arjun responds gently, maybe tells a joke or asks what's wrong.
- 😊 **Happy:** User smiles → Arjun matches the energy, acts enthusiastic.
- 😠 **Angry:** User looks frustrated → Arjun is patient, calm, and de-escalates.
