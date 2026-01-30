# jarvis/commands.py
import json
import os
import requests
import pyperclip
from .paths import paths
from .ai_engine import ai_generate, log_episode

OPEN_ACTIONS = ["open", "launch", "start", "visit", "go to"]
CLOSE_ACTIONS = ["close", "quit", "terminate", "shut down"]

def load_commands():
    if not os.path.exists(paths.commands_file):
        with open(paths.commands_file, "w", encoding="utf-8") as f:
            json.dump({"commands": []}, f, indent=4)
        return []
    try:
        with open(paths.commands_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("commands", [])
    except Exception as e:
        print(f"Error loading commands: {e}")
        return []

def save_commands(commands):
    try:
        with open(paths.commands_file, "w", encoding="utf-8") as f:
            json.dump({"commands": commands}, f, indent=4)
    except Exception as e:
        print(f"Error saving commands: {e}")

def learn_new_command(trigger, audio_mgr, update_gui_status, commands):
    say = audio_mgr.say
    
    if not trigger:
        say("Okay, I'm ready to learn. What is the trigger phrase?")
        update_gui_status("Listening for trigger...")
        trigger = audio_mgr.listen()
        if "none" in trigger:
            say("I didn't catch that. Cancelling.")
            return

    say(f"Got it. When you say '{trigger}', what kind of action should I perform? Say 'open website' or 'run application'.")
    update_gui_status(f"Trigger: '{trigger}'. Listening for action type...")
    action_type = audio_mgr.listen()

    new_command = {"trigger": trigger}

    if "website" in action_type:
        new_command["type"] = "website"
        say("What is the full URL? For example, netflix.com")
        update_gui_status("Listening for URL...")
        target = audio_mgr.listen().replace(" ", "")
        if "none" in target:
            say("I didn't catch that. Cancelling.")
            return
        if not target.startswith("http"):
            target = f"https://{target}"
        new_command["target"] = target

    elif "application" in action_type:
        new_command["type"] = "app"
        say("Please copy the full file path of the application to your clipboard now. Say 'done' when you are ready.")
        update_gui_status("Waiting for clipboard...")

        target = None
        while True:
            status = audio_mgr.listen()
            if any(w in status for w in ["done", "ready"]):
                try:
                    target = pyperclip.paste()
                    if not target.strip():
                        say("Your clipboard is empty. Cancelling.")
                        return
                except Exception as e:
                    print(e)
                    say("I had trouble reading your clipboard. Cancelling.")
                    return
                break
            elif "cancel" in status:
                say("Cancelling.")
                return

        new_command["target"] = target
        say("Thank you. Now, what is the process name for this app? For example, 'notepad.exe'.")
        update_gui_status(f"Launch path: {target}. Listening for process name...")
        process_name = audio_mgr.listen().replace(" ", "")
        if "none" in process_name:
            say("I didn't catch that. Cancelling.")
            return
        if not process_name.endswith(".exe"):
            process_name += ".exe"
        new_command["process_name"] = process_name
    else:
        say("I didn't recognize that action type. Cancelling.")
        return

    commands.append(new_command)
    save_commands(commands)
    say(f"Command saved. When you say '{trigger}', I will perform the action.")

def run_custom_commands(query, commands, audio_mgr, update_gui_status, state):
    say = audio_mgr.say
    for cmd in commands:
        if cmd["trigger"] in query:
            # OPEN
            if any(a in query for a in OPEN_ACTIONS):
                say(f"Opening {cmd['trigger']}...")
                if cmd["type"] == "website":
                    import webbrowser
                    webbrowser.open(cmd["target"])
                elif cmd["type"] == "app":
                    import os
                    try:
                        os.startfile(cmd["target"])
                    except Exception as e:
                        say(f"I couldn't open the file. Check the path.")
                        print(e)
                elif cmd["type"] == "weather":
                    city = cmd["target"]
                    say(f"Getting the weather for {city}...")
                    try:
                        url = f"https://wttr.in/{city}?format=%C+%t+%w"
                        response = requests.get(url)
                        if response.status_code == 200:
                            weather_data = response.text
                            ai_prompt = (
                                "You are a weather reporter. State the following weather data "
                                f"in one simple sentence, starting directly with the conditions: {weather_data}"
                            )
                            ai_generate(ai_prompt, state, say, update_gui_status, speak_result=True)
                        else:
                            say(f"Sorry, I couldn't retrieve the weather for {city}.")
                    except Exception as e:
                        say("Weather service is unreachable.")
                
                # --- FIX: Added the missing arguments here ---
                log_episode(query, f"Opened {cmd['trigger']}", "custom_command_open", True)
                return True

            # CLOSE
            if cmd["type"] == "app" and any(a in query for a in CLOSE_ACTIONS):
                try:
                    if "process_name" in cmd and cmd["process_name"]:
                        import os
                        os.system(f'taskkill /IM "{cmd["process_name"]}" /F')
                        say(f"Closing {cmd['trigger']}.")
                    else:
                        say(f"Sorry, I don't know the process name for {cmd['trigger']}.")
                except Exception as e:
                    print(f"Error closing app: {e}")
                    say(f"Sorry, I had trouble trying to close {cmd['trigger']}.")
                
                # --- FIX: Added the missing arguments here ---
                log_episode(query, f"Closed {cmd['trigger']}", "custom_command_close", True)
                return True
    return False