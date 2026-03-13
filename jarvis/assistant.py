
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

SLEEP_TRIGGERS = ("go to sleep", "stop arjun", "stop listening")
NOTE_ADD_TRIGGERS = ("take a note", "write this down", "make a note")
NOTE_READ_TRIGGERS = ("read my notes", "show my notes", "what are my notes")
FILE_SEARCH_TRIGGERS = ("find file", "search for file", "search file")
GMAIL_SUMMARY_TRIGGERS = ("gmail summary", "summary of my gmail", "gmail ka summary", "inbox summary")
GMAIL_SEARCH_TRIGGERS = ("search gmail for", "gmail search for", "gmail me search", "gmail me dekh")
GMAIL_IMPORTANT_TRIGGERS = ("important emails", "starred emails", "gmail important", "gmail starred")
GMAIL_ATTACH_TRIGGERS = ("email attachments", "attachments in gmail", "koi attachment aya", "any new attachments")
SYSTEM_STATUS_TRIGGERS = ("system status", "system stats", "cpu usage", "ram usage")
VOL_UP_TRIGGERS = ("increase volume", "increase the volume", "volume up")
VOL_DOWN_TRIGGERS = ("decrease volume", "decrease the volume", "volume down", "lower volume")
BRIGHT_UP_TRIGGERS = ("increase brightness", "brightness up")
BRIGHT_DOWN_TRIGGERS = ("decrease brightness", "brightness down", "lower brightness")
JOKE_TRIGGERS = ("tell me a joke", "say a joke", "make me laugh")
SHUTDOWN_TRIGGERS = ("shutdown", "turn off", "power off")
RESTART_TRIGGERS = ("restart", "reboot")
SELF_IMPROVE_TRIGGERS = ("optimize yourself", "improve yourself", "update yourself", "upgrade yourself")

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

    def _contains_any(self, text, phrases):
        return any(p in text for p in phrases)

    def _say_by_persona(self, friendly_text: str, jarvis_text: str | None = None):
        self.audio.say(jarvis_text if self.state.current_persona == "jarvis" and jarvis_text else friendly_text)

    def _try_handle_query(self, query: str, lower_q: str):
        if self._contains_any(lower_q, SLEEP_TRIGGERS):
            self._say_by_persona("Going to sleep.", "Entering sleep mode.")
            self.audio.set_sleep(True)
            self.gui_queue.put("STATE:SLEEPING")
            return "handled"

        if run_custom_commands(query, self.commands, self.audio, self.update_gui_status, self.state):
            return "handled"

        if "learn a new command" in lower_q or "new command" in lower_q:
            learn_new_command(trigger=None, audio_mgr=self.audio, update_gui_status=self.update_gui_status, commands=self.commands)
            save_commands(self.commands)
            return "handled"

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
            return "handled"

        if "arjun remember" in lower_q or "remember this" in lower_q:
            ok, msg = remember_fact(query)
            self.audio.say(msg)
            if ok:
                load_memory(self.state)
            return "handled"

        if self._contains_any(lower_q, NOTE_ADD_TRIGGERS):
            take_note(self.audio)
            return "handled"
        if self._contains_any(lower_q, NOTE_READ_TRIGGERS):
            read_notes(self.audio)
            return "handled"

        if self._contains_any(lower_q, FILE_SEARCH_TRIGGERS):
            find_file(self.audio, self.update_gui_status)
            return "handled"

        if self._contains_any(lower_q, GMAIL_SUMMARY_TRIGGERS):
            self.update_gui_status("Fetching Gmail summary...")
            self.audio.say(gmail_summary_text())
            return "handled"
        if self._contains_any(lower_q, GMAIL_SEARCH_TRIGGERS):
            self.update_gui_status("Searching your Gmail...")
            self.audio.say(gmail_search_text(query))
            return "handled"
        if self._contains_any(lower_q, GMAIL_IMPORTANT_TRIGGERS):
            self.update_gui_status("Checking important emails...")
            self.audio.say(gmail_important_text())
            return "handled"
        if self._contains_any(lower_q, GMAIL_ATTACH_TRIGGERS):
            self.update_gui_status("Checking recent email attachments...")
            self.audio.say(gmail_attachments_text(days=7))
            return "handled"

        if handle_whatsapp_command(query, self.audio, self.update_gui_status):
            return "handled"

        if check_command(lower_q, ["play", "open", "start"], ["music", "song", "track"]):
            self._say_by_persona("Starting your music.", "Starting music playback.")
            music_path = r"C:\Users\PURJEET\Downloads\song.mp3"
            try:
                import os
                os.system(f"start {music_path}")
            except Exception as e:
                print(e)
                self.audio.say("I couldn't play that music file.")
            return "handled"

        if ("what is" in lower_q and "my name" in lower_q) or "who am i" in lower_q:
            if self.state.user_name:
                self._say_by_persona(f"Your name is {self.state.user_name}.", f"Your name: {self.state.user_name}.")
            else:
                self.audio.say("I don't know your name yet. You can tell me by saying 'Arjun remember my name is...'")
            return "handled"

        if check_command(lower_q, ["what is", "tell me"], ["the time"]):
            now = datetime.datetime.now().strftime('%H:%M:%S')
            self._say_by_persona(f"The time is {now}", f"Time: {now}.")
            return "handled"

        if simple_weather(lower_q, self.audio, self.state, self.update_gui_status):
            return "handled"

        if "wake me up at" in lower_q or "set an alarm for" in lower_q:
            set_alarm(query, self.audio)
            return "handled"
        if "set a timer for" in lower_q:
            set_timer(query, self.audio)
            return "handled"

        if "latest news" in lower_q or "news headlines" in lower_q:
            speak_latest_news(self.audio, self.state, self.update_gui_status)
            return "handled"

        if self._contains_any(lower_q, SYSTEM_STATUS_TRIGGERS):
            speak_system_status(self.audio)
            return "handled"
        if self._contains_any(lower_q, VOL_UP_TRIGGERS):
            volume_up(self.audio)
            return "handled"
        if self._contains_any(lower_q, VOL_DOWN_TRIGGERS):
            volume_down(self.audio)
            return "handled"

        if "pause" in lower_q or "play" in lower_q:
            media_playpause(self.audio)
            return "handled"
        if "next song" in lower_q or "next track" in lower_q:
            media_next(self.audio)
            return "handled"
        if "previous song" in lower_q or "previous track" in lower_q:
            media_prev(self.audio)
            return "handled"

        if self._contains_any(lower_q, BRIGHT_UP_TRIGGERS):
            brightness_up(self.audio)
            return "handled"
        if self._contains_any(lower_q, BRIGHT_DOWN_TRIGGERS):
            brightness_down(self.audio)
            return "handled"

        if self._contains_any(lower_q, JOKE_TRIGGERS):
            tell_joke(self.audio)
            return "handled"

        if self._contains_any(lower_q, SHUTDOWN_TRIGGERS):
            shutdown_pc(self.audio)
            return "handled"
        if self._contains_any(lower_q, RESTART_TRIGGERS):
            restart_pc(self.audio)
            return "handled"

        if "arjun quit" in lower_q or "exit" in lower_q:
            self._say_by_persona("Goodbye. Shutting down.", "Shutting down.")
            self.gui_queue.put("QUIT")
            return "quit"

        if "jarvis" in lower_q and (any(w in lower_q for w in ["mode", "style", "switch", "change", "become", "mod"]) or lower_q.strip() == "jarvis"):
            self.set_persona("jarvis")
            return "handled"

        if "friendly" in lower_q or "friend mode" in lower_q or ("normal" in lower_q and "mode" in lower_q) or "back to normal" in lower_q:
            self.set_persona("friendly")
            return "handled"

        if "reset chat" in lower_q:
            self.audio.say("Chat history has been reset.")
            load_memory(self.state)
            return "handled"

        if self._contains_any(lower_q, SELF_IMPROVE_TRIGGERS):
            self.audio.say("Okay, I will review recent interactions and try to improve.")
            self_evaluate_and_improve(self.state, self.audio.say)
            return "handled"

        ai_chat(query, self.state, self.audio.say, self.update_gui_status)
        return "handled"

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
            self._say_by_persona("I am online and ready.", "Online.")

    def run(self):
        self.update_gui_status("Arjun A.I is ready.")
        self.audio.say("Welcome to Arjun A.I. I have loaded your custom commands.")

        try:
            while True:
                self._handle_sleep_toggle()

                if self.audio.is_asleep:
                    query = self.audio.listen()
                    if "hey arjun" in query or "wake up" in query:
                        self.audio.set_sleep(False)
                        self.gui_queue.put("STATE:AWAKE")
                        self._say_by_persona("I am online and ready.", "Online.")
                    continue

                query = self.audio.listen()
                if "none" in query:
                    continue

                lower_q = query.lower()
                route = self._try_handle_query(query, lower_q)
                if route == "quit":
                    break

        finally:
            self.audio.cleanup()
            pythoncom.CoUninitialize()
