
import os
import re
import random
import datetime
import threading
import requests
import psutil
import pyautogui
import screen_brightness_control as sbc
from newsapi import NewsApiClient
import config
from .paths import paths
from .ai_engine import ai_generate

CONFIRM_WORDS = ["yes", "yeah", "yep", "sure", "open it", "please", "okay", "do it"]

def check_command(query, action_words, subject_words):
    query = query.lower()
    return any(a in query for a in action_words) and any(s in query for s in subject_words)

def take_note(audio_mgr):
    say = audio_mgr.say
    say("What should I write down?")
    note = audio_mgr.listen()
    if "none" in note:
        say("I didn't catch that. Note cancelled.")
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(paths.notes_file, "a", encoding="utf-8") as f:
        f.write(f"{now}: {note}\n")
    say("Note saved.")

def read_notes(audio_mgr):
    say = audio_mgr.say
    say("Reading your notes...")
    try:
        with open(paths.notes_file, "r", encoding="utf-8") as f:
            notes = f.read()
        if notes:
            say(notes)
        else:
            say("Your note file is empty.")
    except FileNotFoundError:
        say("I couldn't find any notes.")

def find_file(audio_mgr, update_gui_status):
    say = audio_mgr.say

    say("What is the name of the file you are looking for?")
    update_gui_status("Listening for filename...")
    filename = audio_mgr.listen()
    if "none" in filename:
        say("I didn't catch that. Cancelling.")
        return
    filename = filename.replace(" dot ", ".")

    say("Which folder should I search? For example, Documents, Downloads, or Desktop.")
    update_gui_status(f"File: {filename}. Listening for folder...")
    folder_name = audio_mgr.listen()
    if "none" in folder_name:
        say("I didn't catch that. Cancelling.")
        return

    search_path = paths.get_user_folder(folder_name)
    if not os.path.exists(search_path):
        say(f"Sorry, I couldn't find a folder named {folder_name}.")
        return

    say(f"Okay, searching your {folder_name} folder for {filename}. This may take a moment.")
    update_gui_status(f"Searching for {filename}...")

    found = None
    for root, _, files in os.walk(search_path):
        for file in files:
            if filename.lower() in file.lower():
                found = os.path.join(root, file)
                break
        if found:
            break

    if not found:
        say(f"Sorry, I searched your {folder_name} folder but could not find {filename}.")
        update_gui_status("File not found.")
        return

    say("I found the file!")
    update_gui_status(f"Found: {found}")
    say("Would you like me to open it?")
    confirm = audio_mgr.listen()
    if any(w in confirm for w in CONFIRM_WORDS):
        try:
            os.startfile(found)
            say("Opening the file.")
        except Exception as e:
            print(e)
            say("Sorry, I found the file but I am unable to open it.")
    else:
        say("Okay, I will not open it.")

def _timer_end(duration_str, audio_mgr):
    audio_mgr.say(f"Your timer for {duration_str} is up.")

def _alarm_end(time_str, audio_mgr):
    audio_mgr.say(f"This is your alarm for {time_str}.")

def set_alarm(query, audio_mgr):
    say = audio_mgr.say
    match = re.search(r"at\s+(\d{1,2})(?:\s*:?\s*(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", query, re.IGNORECASE)
    if not match:
        say("Sorry, I didn't catch that. Please specify a time with AM or PM.")
        return

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3).lower().replace(".", "")

    time_str = f"{hour}:{minute:02d} {meridiem.upper()}"

    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    now = datetime.datetime.now()
    alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if alarm_time <= now:
        alarm_time += datetime.timedelta(days=1)

    duration = (alarm_time - now).total_seconds()
    threading.Timer(duration, _alarm_end, args=[time_str, audio_mgr]).start()
    say(f"Understood. I've set an alarm for {time_str}.")

def set_timer(query, audio_mgr):
    say = audio_mgr.say
    match = re.search(r"(\d+)\s+(sec|second|min|minute|hour)s?", query, re.IGNORECASE)
    if not match:
        say("Sorry, I didn't understand the duration. Please say 'set a timer for 5 minutes' or '10 seconds'.")
        return

    value = int(match.group(1))
    unit = match.group(2).lower()
    
    if unit.startswith("sec"):
        seconds = value
        unit_str = "seconds"
    elif unit.startswith("min"):
        seconds = value * 60
        unit_str = "minutes"
    else:
        seconds = value * 3600
        unit_str = "hours"

    duration_str = f"{value} {unit_str}"
    threading.Timer(seconds, _timer_end, args=[duration_str, audio_mgr]).start()
    say(f"Okay, timer set for {duration_str}.")

def simple_weather(query, audio_mgr, state, update_gui_status):
    say = audio_mgr.say
    lower_q = query.lower()
    
    if not any(w in lower_q for w in ["weather", "temperature", "temp", "mausam", "vedar", "wether"]):
        return False
        
    city = None
    
    # List of search patterns (most specific to least specific)
    patterns = [
        r"(?:weather|temperature|temp|mausam|vedar|wether)\s+(?:today\s+)?(?:in|of|at|for|ka|ki|me|mein)\s+([a-z\s]+)",
        r"([a-z\s]+?)\s+(?:ka|ki|me|mein)?\s*(?:weather|temperature|temp|mausam|vedar|wether)",
        r"(?:weather|temperature|temp|mausam|vedar|wether)\s+([a-z]+)"
    ]
    
    excluded_words = ("today", "tomorrow", "now", "current", "report", "forecast", "like", "in", "of", "kya", "hai", "bata", "batao", "dikha", "dikhao", "please")
    
    for pattern in patterns:
        match = re.search(pattern, lower_q)
        if match:
            candidate = match.group(1).strip()
            # If the entire candidate is an excluded word, skip it
            if candidate not in excluded_words:
                city = candidate
                break
                
    if not city:
        city = "Delhi"
        
    # Clean up city name from common extra words
    cleanup_pattern = r"\b(" + "|".join(excluded_words) + r")\b"
    city = re.sub(cleanup_pattern, "", city).strip()
    
    if not city:
        city = "Delhi"
        
    try:
        say(f"Getting the weather for {city}...")
        url = f"https://wttr.in/{city}?format=%C+%t+%w"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            say("Sorry, I couldn't retrieve the weather for that location.")
            return True
        weather_data = resp.text.strip()
        prompt = (
            "You are a weather reporter. State the following weather data "
            f"in one simple sentence, starting directly with the conditions: {weather_data}"
        )
        ai_generate(prompt, state, say, update_gui_status, speak_result=True)
        return True
    except Exception as e:
        print(e)
        say("Sorry, I had trouble connecting to the weather service.")
        return True

def get_backup_news():
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        titles = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            # Clean up source site name at the end (e.g. "- Times of India")
            title_clean = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
            titles.append(f"- {title_clean}")
        if titles:
            return titles, None
    except Exception as e:
        print(f"Backup news error: {e}")
    return None, "I had trouble connecting to the news service."

def get_latest_news():
    # NewsAPI has been failing, so we default to Google News RSS directly
    return get_backup_news()

def speak_latest_news(audio_mgr, state, update_gui_status):
    say = audio_mgr.say
    titles, err = get_latest_news()
    if err:
        say(err)
        return
    joined = "Here are the top headlines:\n" + "\n".join(titles)
    prompt = (
        "You are an AI assistant. Here are the top news headlines: "
        f"'{joined}'. Please read the top 3 headlines to the user in a natural and engaging way. "
        "Do NOT add conversational greetings or use words like 'Sir' or 'Bhai'. Just state the news."
    )
    ai_generate(prompt, state, say, update_gui_status, speak_result=True)

def speak_system_status(audio_mgr):
    say = audio_mgr.say
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        say(f"System is at {cpu} percent CPU usage and {ram} percent RAM usage.")
    except Exception as e:
        print(e)
        say("Sorry, I am unable to check system status right now.")

def volume_up(audio_mgr):
    say = audio_mgr.say
    try:
        say("Increasing volume.")
        for _ in range(5):
            pyautogui.press("volumeup")
    except Exception as e:
        print(e)
        say("Sorry, I couldn't change the volume.")

def volume_down(audio_mgr):
    say = audio_mgr.say
    try:
        say("Decreasing volume.")
        for _ in range(5):
            pyautogui.press("volumedown")
    except Exception as e:
        print(e)
        say("Sorry, I couldn't change the volume.")

def media_playpause(audio_mgr):
    say = audio_mgr.say
    say("Okay.")
    pyautogui.press("playpause")

def media_next(audio_mgr):
    say = audio_mgr.say
    say("Next track.")
    pyautogui.hotkey("ctrl", "right")

def media_prev(audio_mgr):
    say = audio_mgr.say
    say("Previous track.")
    pyautogui.hotkey("ctrl", "left")

def brightness_up(audio_mgr):
    say = audio_mgr.say
    try:
        current = sbc.get_brightness()
        if not current:
            say("Sorry, I am unable to get brightness data.")
            return
        new = min(100, current[0] + 10)
        sbc.set_brightness(new)
        say(f"Brightness set to {new} percent")
    except Exception as e:
        print(e)
        say("Sorry, I am unable to control brightness on this device.")

def brightness_down(audio_mgr):
    say = audio_mgr.say
    try:
        current = sbc.get_brightness()
        if not current:
            say("Sorry, I am unable to get brightness data.")
            return
        new = max(0, current[0] - 10)
        sbc.set_brightness(new)
        say(f"Brightness set to {new} percent")
    except Exception as e:
        print(e)
        say("Sorry, I am unable to control brightness on this device.")

def tell_joke(audio_mgr):
    say = audio_mgr.say
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "What do you call fake spaghetti? An Impasta!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
    ]
    say(random.choice(jokes))

def shutdown_pc(audio_mgr):
    say = audio_mgr.say
    say("Are you sure you want to shutdown the system?")
    confirm = audio_mgr.listen()
    if any(w in confirm for w in CONFIRM_WORDS):
        say("Shutting down the system. Goodbye.")
        os.system("shutdown /s /t 1")
    else:
        say("Shutdown cancelled.")

def restart_pc(audio_mgr):
    say = audio_mgr.say
    say("Are you sure you want to restart the system?")
    confirm = audio_mgr.listen()
    if any(w in confirm for w in CONFIRM_WORDS):
        say("Restarting the system.")
        os.system("shutdown /r /t 1")
    else:
        say("Restart cancelled.")

def extract_youtube_search_query(query: str) -> str:
    clean_query = query.lower()
    
    # Robust removal of platform words, action verbs, and filler particles
    patterns_to_remove = [
        r'\byoutube\s*(par|pe|me|on|in)?\b',
        r'\b(play|chala|chla|chalao|laga|lagao|baja|bajao|start)\b',
        r'\b(video|song|gana|music|karo|please|dekh|dikhao|search|for|about|on|the)\b',
        r'\b(ka|ke|ki|ek|koi)\b', 
    ]
    
    for pattern in patterns_to_remove:
        clean_query = re.sub(pattern, " ", clean_query, flags=re.IGNORECASE)
        
    # Clean up extra spaces
    clean_query = re.sub(r'\s+', ' ', clean_query).strip()
    return clean_query

def search_youtube(query: str, audio_mgr):
    say = audio_mgr.say
    search_term = extract_youtube_search_query(query)
    if not search_term:
        say("What would you like to search on YouTube?")
        return
    
    say(f"Searching YouTube for {search_term}.")
    import webbrowser
    import urllib.parse
    encoded = urllib.parse.quote(search_term)
    webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")

def play_youtube_video(query: str, audio_mgr):
    say = audio_mgr.say
    search_term = extract_youtube_search_query(query)
    
    # Strip any extra action words like play, chalao, bajao, etc.
    search_term = re.sub(r"^(play|chalao|start|chalaye|baja|bajao)\b", "", search_term).strip()
    search_term = re.sub(r"\b(play|chalao|start|chalaye|baja|bajao)$", "", search_term).strip()
    
    if not search_term:
        say("What would you like me to play on YouTube?")
        return
        
    say(f"Playing {search_term} on YouTube.")
    
    import threading
    def _bg_play():
        try:
            import urllib.request
            import urllib.parse
            import re
            import webbrowser
            
            encoded = urllib.parse.quote(search_term)
            html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={encoded}")
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            
            if video_ids:
                url = "https://www.youtube.com/watch?v=" + video_ids[0]
                webbrowser.open(url)
            else:
                webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
        except Exception as e:
            print(f"YouTube play error: {e}")
            import webbrowser
            import urllib.parse
            encoded = urllib.parse.quote(search_term)
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
            
    threading.Thread(target=_bg_play, daemon=True).start()

def speak_with_llm(raw_text: str, prefix: str, audio_mgr, state, update_gui_status):
    say = audio_mgr.say
    if "trouble" in raw_text or "couldn't" in raw_text or "no new" in raw_text or "don't seem" in raw_text or "no emails" in raw_text:
        say(raw_text)
        return
        
    prompt = (
        f"You are an AI assistant. {prefix}: '{raw_text}'. Read this out naturally and concisely. "
        "Do NOT add any conversational greetings, intros like 'Kya haal hai', 'Bhai', or 'Sir'. "
        "Do NOT repeat the information. Just directly deliver the content once."
    )
    ai_generate(prompt, state, say, update_gui_status, speak_result=True)

