
import speech_recognition as sr
import pyttsx3
import os
import json
import vosk
from jarvis.paths import paths

vosk.SetLogLevel(-1)

class AudioManager:
    def __init__(self, update_gui_status):
        self.update_gui_status = update_gui_status
        self.recognizer = sr.Recognizer()
        self.is_asleep = False
        self.voice_profile = "friendly"

        self.model_path = os.path.join(paths.PROJECT_DIR, "model")
        self.offline_mode = False
        self.vosk_model = None

        if os.path.exists(self.model_path):
            try:
                self.update_gui_status("Loading offline backup...")
                self.vosk_model = vosk.Model(self.model_path)
                self.offline_mode = True
                print("Vosk model loaded (Backup).")
            except Exception as e:
                print(f"Error loading Vosk: {e}")
        else:
            print("No offline model found.")

        self._init_mic()

    def _init_mic(self):
        self.update_gui_status("Calibrating microphone...")
        try:
            with sr.Microphone() as source:

                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
        except Exception as e:
            print(f"Mic error: {e}")

    def say(self, text: str):

        display_name = "Jarvis" if self.voice_profile == "jarvis" else "Arjun"
        self.update_gui_status(f"{display_name}: {text}")
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []

            idx = 1 if len(voices) > 1 and self.voice_profile == "jarvis" else 0
            if voices:
                engine.setProperty("voice", voices[idx].id)
            engine.setProperty("rate", 165 if self.voice_profile == "jarvis" else 185)

            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"TTS error: {e}")

    def listen(self) -> str:
        with sr.Microphone() as source:
            if not self.is_asleep:
                self.update_gui_status("Listening...")

            try:
                self.recognizer.pause_threshold = 1.0
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return "none"

        query = ""
        if not self.is_asleep:
            self.update_gui_status("Recognizing...")

        try:
            query = self.recognizer.recognize_google(audio, language="en-in")
        except:

            if self.offline_mode and self.vosk_model:
                try:
                    raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
                    rec.AcceptWaveform(raw_data)
                    result_json = rec.FinalResult()
                    data = json.loads(result_json)
                    query = data.get("text", "")
                except:
                    pass

        if not query:
            return "none"

        query = query.lower()
        if not self.is_asleep:
            self.update_gui_status(f"User said: {query}")
        return query

    def set_sleep(self, sleep: bool):
        self.is_asleep = sleep

    def cleanup(self):
        pass

    def set_voice_profile(self, profile: str):
        profile = (profile or "").lower()
        if profile in ("friendly", "jarvis"):
            self.voice_profile = profile
