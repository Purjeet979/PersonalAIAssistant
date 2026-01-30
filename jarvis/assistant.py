# jarvis/assistant.py
import threading
import datetime
import pythoncom
from .audio import AudioManager
from .whatsapp import handle_whatsapp_command
from jarvis.logger import log_episode
from .memory import MemoryState, load_memory, remember_fact
from .ai_engine import chat as ai_chat, ai_generate, self_evaluate_and_improve
from .commands import load_commands, save_commands, learn_new_command, run_custom_commands
from .features import (
    check_command,
    take_note, read_notes, find_file,
    set_alarm, set_timer, simple_weather,
    speak_latest_news, speak_system_status,
    volume_up, volume_down,
    media_playpause, media_next, media_prev,
    brightness_up, brightness_down,
    tell_joke, shutdown_pc, restart_pc,
)
from .gmail_tools import (
    gmail_summary_text,
    gmail_search_text,
    gmail_important_text,
    gmail_attachments_text,
)


class JarvisAssistant:
    def __init__(self, gui_queue, update_gui_status):
        self.gui_queue = gui_queue
        self.update_gui_status = update_gui_status
        self.audio = AudioManager(update_gui_status)
        self.audio.set_voice_profile("friendly")
        self.state = MemoryState()
        load_memory(self.state)
        self.commands = load_commands()
        self.force_sleep_toggle = False
        self.display_name = "Arjun"

    def set_persona(self, mode: str):
        mode = (mode or "").lower().strip()

        if mode in ("friendly", "friend", "companion"):
            self.state.current_persona = "friendly"
            self.state.rebuild_prompt()
            self.audio.set_voice_profile("friendly")
            self.display_name = "Arjun"
            self.audio.say("Okay, switching to friendly companion mode.")
            self.gui_queue.put("MODE:FRIENDLY")
            self.gui_queue.put("WAKEWORD:Arjun")

        elif mode in ("jarvis", "assistant", "formal"):
            self.state.current_persona = "jarvis"
            self.state.rebuild_prompt()
            self.audio.set_voice_profile("jarvis")
            self.display_name = "Jarvis"
            self.audio.say("Jarvis mode activated.")
            self.gui_queue.put("MODE:JARVIS")
            self.gui_queue.put("WAKEWORD:Jarvis")

        else:
            self.audio.say("I don't recognise that personality mode.")

    def toggle_sleep(self):
        self.force_sleep_toggle = True

    def _handle_sleep_toggle(self):
        if not self.force_sleep_toggle:
            return
        self.force_sleep_toggle = False
        new_state = not self.audio.is_asleep
        self.audio.set_sleep(new_state)
        if new_state:
            self.gui_queue.put("STATE:SLEEPING")
        else:
            self.gui_queue.put("STATE:AWAKE")
            self.audio.say("I am online and ready, sir.")

    def run(self):
        self.update_gui_status("Arjun A.I is ready.")
        self.audio.say("Welcome to Arjun A.I. I have loaded your custom commands.")

        try:
            while True:
                self._handle_sleep_toggle()

                # Sleep mode: only wake word
                if self.audio.is_asleep:
                    query = self.audio.listen()
                    if "hey arjun" in query or "wake up" in query:
                        self.audio.set_sleep(False)
                        self.gui_queue.put("STATE:AWAKE")
                        self.audio.say("I am online and ready, sir.")
                    continue

                query = self.audio.listen()
                if "none" in query:
                    continue

                lower_q = query.lower()

                # Put to sleep
                if any(t in lower_q for t in ["go to sleep", "stop arjun", "stop listening"]):
                    self.audio.say("Going to sleep, sir.")
                    self.audio.set_sleep(True)
                    self.gui_queue.put("STATE:SLEEPING")
                    continue

                # Custom commands
                if run_custom_commands(query, self.commands, self.audio, self.update_gui_status, self.state):
                    continue

                # Learn new command (manual)
                if "learn a new command" in lower_q or "new command" in lower_q:
                    learn_new_command(
                        trigger=None,
                        audio_mgr=self.audio,
                        update_gui_status=self.update_gui_status,
                        commands=self.commands,
                    )
                    save_commands(self.commands)
                    continue

                # Clipboard read
                if "read my clipboard" in lower_q or "what's on my clipboard" in lower_q:
                    import pyperclip
                    try:
                        text = pyperclip.paste()
                        if text:
                            self.audio.say("Your clipboard contains the following text:")
                            self.audio.say(text)
                        else:
                            self.audio.say("Your clipboard is empty.")
                    except Exception as e:
                        print(e)
                        self.audio.say("I had trouble reading your clipboard.")
                    continue

                # Memory
                if "arjun remember" in lower_q or "remember this" in lower_q:
                    ok, msg = remember_fact(query)
                    self.audio.say(msg)
                    if ok:
                        load_memory(self.state)
                    continue

                # Notes
                if any(t in lower_q for t in ["take a note", "write this down", "make a note"]):
                    take_note(self.audio)
                    continue
                if any(t in lower_q for t in ["read my notes", "show my notes", "what are my notes"]):
                    read_notes(self.audio)
                    continue

                # File search
                if any(t in lower_q for t in ["find file", "search for file", "search file"]):
                    find_file(self.audio, self.update_gui_status)
                    continue

                # ----------------- GMAIL FEATURES ----------------- #

                # Gmail summary
                if any(
                    phrase in lower_q
                    for phrase in [
                        "gmail summary",
                        "summary of my gmail",
                        "gmail ka summary",
                        "inbox summary",
                    ]
                ):
                    self.update_gui_status("Fetching Gmail summary...")
                    text = gmail_summary_text()
                    self.audio.say(text)
                    continue

                # Gmail search
                if any(
                    phrase in lower_q
                    for phrase in [
                        "search gmail for",
                        "gmail search for",
                        "gmail me search",
                        "gmail me dekh",
                    ]
                ):
                    self.update_gui_status("Searching your Gmail...")
                    text = gmail_search_text(query)
                    self.audio.say(text)
                    continue

                # Important / starred emails
                if any(
                    phrase in lower_q
                    for phrase in [
                        "important emails",
                        "starred emails",
                        "gmail important",
                        "gmail starred",
                    ]
                ):
                    self.update_gui_status("Checking important emails...")
                    text = gmail_important_text()
                    self.audio.say(text)
                    continue

                # Attachment alerts
                if any(
                    phrase in lower_q
                    for phrase in [
                        "email attachments",
                        "attachments in gmail",
                        "koi attachment aya",
                        "any new attachments",
                    ]
                ):
                    self.update_gui_status("Checking recent email attachments...")
                    text = gmail_attachments_text(days=7)
                    self.audio.say(text)
                    continue

                # WhatsApp messaging (semi-automatic)
                if handle_whatsapp_command(query, self.audio, self.update_gui_status):
                    continue

                # Music (your single track)
                if check_command(lower_q, ["play", "open", "start"], ["music", "song", "track"]):
                    self.audio.say("Starting your music, sir.")
                    music_path = r"C:\Users\PURJEET\Downloads\song.mp3"
                    try:
                        import os
                        os.system(f"start {music_path}")
                    except Exception as e:
                        print(e)
                        self.audio.say("I couldn't play that music file.")
                    continue

                # Name
                if ("what is" in lower_q and "my name" in lower_q) or "who am i" in lower_q:
                    if self.state.user_name:
                        self.audio.say(f"Your name is {self.state.user_name}, sir.")
                    else:
                        self.audio.say(
                            "I don't know your name yet. You can tell me by saying 'Arjun remember my name is...'"
                        )
                    continue

                # Time
                if check_command(lower_q, ["what is", "tell me"], ["the time"]):
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    self.audio.say(f"Sir, the time is {now}")
                    continue

                # Weather
                if simple_weather(lower_q, self.audio, self.state, self.update_gui_status):
                    continue

                # Alarm / Timer
                if "wake me up at" in lower_q or "set an alarm for" in lower_q:
                    set_alarm(query, self.audio)
                    continue
                if "set a timer for" in lower_q:
                    set_timer(query, self.audio)
                    continue

                # News
                if "latest news" in lower_q or "news headlines" in lower_q:
                    speak_latest_news(self.audio, self.state, self.update_gui_status)
                    continue

                # System status
                if any(t in lower_q for t in ["system status", "system stats", "cpu usage", "ram usage"]):
                    speak_system_status(self.audio)
                    continue

                # Volume
                if any(t in lower_q for t in ["increase volume", "increase the volume", "volume up"]):
                    volume_up(self.audio)
                    continue
                if any(t in lower_q for t in ["decrease volume", "decrease the volume", "volume down", "lower volume"]):
                    volume_down(self.audio)
                    continue

                # Media controls
                if "pause" in lower_q or "play" in lower_q:
                    media_playpause(self.audio)
                    continue
                if "next song" in lower_q or "next track" in lower_q:
                    media_next(self.audio)
                    continue
                if "previous song" in lower_q or "previous track" in lower_q:
                    media_prev(self.audio)
                    continue

                # Brightness
                if any(t in lower_q for t in ["increase brightness", "brightness up"]):
                    brightness_up(self.audio)
                    continue
                if any(t in lower_q for t in ["decrease brightness", "brightness down", "lower brightness"]):
                    brightness_down(self.audio)
                    continue

                # Jokes
                if any(t in lower_q for t in ["tell me a joke", "say a joke", "make me laugh"]):
                    tell_joke(self.audio)
                    continue

                # Power
                if any(t in lower_q for t in ["shutdown", "turn off", "power off"]):
                    shutdown_pc(self.audio)
                    continue
                if any(t in lower_q for t in ["restart", "reboot"]):
                    restart_pc(self.audio)
                    continue

                # Exit
                if "arjun quit" in lower_q or "exit" in lower_q:
                    self.audio.say("Goodbye sir. Shutting down.")
                    self.gui_queue.put("QUIT")
                    break

                # -------- Persona switches (robust) --------
                # Switch TO JARVIS
                if (
                    "jarvis" in lower_q
                    and (
                        any(w in lower_q for w in ["mode", "style", "switch", "change", "become", "mod"])
                        or lower_q.strip() == "jarvis"
                    )
                ):
                    self.set_persona("jarvis")
                    continue

                # Switch TO FRIENDLY
                if (
                    "friendly" in lower_q
                    or "friend mode" in lower_q
                    or ("normal" in lower_q and "mode" in lower_q)
                    or "back to normal" in lower_q
                ):
                    self.set_persona("friendly")
                    continue

                # Reset chat
                if "reset chat" in lower_q:
                    self.audio.say("Chat history has been reset.")
                    load_memory(self.state)
                    continue

                # Self optimise
                if any(
                    t in lower_q
                    for t in ["optimize yourself", "improve yourself", "update yourself", "upgrade yourself"]
                ):
                    self.audio.say("Okay, I will review recent interactions and try to improve.")
                    self_evaluate_and_improve(self.state, self.audio.say)
                    continue

                # Fallback: chat LLM
                ai_chat(query, self.state, self.audio.say, self.update_gui_status)

        finally:
            self.audio.cleanup()
            pythoncom.CoUninitialize()
