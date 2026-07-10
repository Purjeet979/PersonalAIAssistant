
import speech_recognition as sr
import pyttsx3
import os
import json
import vosk
import asyncio
import edge_tts
import ctypes
import re
from jarvis.paths import paths

vosk.SetLogLevel(-1)

def play_audio_mci(file_path):
    abs_path = os.path.abspath(file_path)
    try:
        ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias myaudio', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('play myaudio wait', None, 0, None)
        ctypes.windll.winmm.mciSendStringW('close myaudio', None, 0, None)
    except Exception as e:
        print(f"MCI playback error: {e}")

async def _generate_speech(text: str, voice: str, path: str, rate: str = "+0%"):
    clean_text = re.sub(r"\*\*|\*", "", text)
    clean_text = re.sub(r"<thought>.*?</thought>", "", clean_text, flags=re.DOTALL).strip()
    if not clean_text:
        clean_text = "Hmm."
    communicate = edge_tts.Communicate(clean_text, voice, rate=rate)
    await communicate.save(path)

def split_into_sentences(text: str) -> list[str]:
    # Split by periods, exclamation marks, question marks, and Hindi full stops followed by spaces
    sentences = re.split(r'(?<=[.!?|])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

class AudioManager:
    def __init__(self, update_gui_status):
        self.update_gui_status = update_gui_status
        self.recognizer = sr.Recognizer()
        self.is_asleep = False
        self.voice_profile = "friendly"
        
        import threading
        self.speak_lock = threading.Lock()

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
        import queue
        import threading

        with self.speak_lock:
            display_name = "Jarvis" if self.voice_profile == "jarvis" else "Arjun"

            # Choose the neural voice and speech rate
            voice = "en-GB-SoniaNeural" if self.voice_profile == "jarvis" else "hi-IN-MadhurNeural"
            rate = "+0%" if self.voice_profile == "jarvis" else "+70%"

            sentences = split_into_sentences(text)
            if not sentences:
                return

            q = queue.Queue()

            def downloader():
                for i, s in enumerate(sentences):
                    path = os.path.join(paths.PROJECT_DIR, f"temp_speech_{i}.mp3")
                    try:
                        if os.path.exists(path):
                            try:
                                os.remove(path)
                            except Exception:
                                pass
                        asyncio.run(_generate_speech(s, voice, path, rate))
                        if os.path.exists(path) and os.path.getsize(path) > 0:
                            q.put((path, s))
                        else:
                            q.put((None, s))
                    except Exception as e:
                        print(f"Edge TTS download thread error: {e}")
                        q.put((None, s))
                q.put((None, None))  # Sentinel

            t = threading.Thread(target=downloader, daemon=True)
            t.start()
            
            first_sentence = True
            fallback_engine = None

            while True:
                path, s = q.get()
                if path is None and s is None:
                    break
                
                # Show the text exactly when the first audio chunk is ready to play
                if first_sentence:
                    self.update_gui_status(f"{display_name}: {text}")
                    first_sentence = False

                if path:
                    play_audio_mci(path)
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                else:
                    try:
                        if fallback_engine is None:
                            fallback_engine = pyttsx3.init()
                            voices = fallback_engine.getProperty("voices") or []
                            idx = 1 if len(voices) > 1 and self.voice_profile == "jarvis" else 0
                            if voices:
                                fallback_engine.setProperty("voice", voices[idx].id)
                            fallback_engine.setProperty("rate", 165 if self.voice_profile == "jarvis" else 277)
                        
                        fallback_engine.say(s)
                        fallback_engine.runAndWait()
                    except Exception as e:
                        print(f"Offline fallback TTS error: {e}")

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
