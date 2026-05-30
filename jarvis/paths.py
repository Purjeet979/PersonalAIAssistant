
import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

@dataclass
class Paths:

    PROJECT_DIR: str = PROJECT_DIR

    memory_file: str = os.path.join(PROJECT_DIR, "arjun_memory.txt")
    commands_file: str = os.path.join(PROJECT_DIR, "custom_commands.json")
    notes_file: str = os.path.join(PROJECT_DIR, "notes.txt")
    episode_log: str = os.path.join(PROJECT_DIR, "episodes.jsonl")
    improvements_file: str = os.path.join(PROJECT_DIR, "improvements.txt")
    openai_dir: str = os.path.join(PROJECT_DIR, "Openai")
    assistant_gif: str = os.path.join(PROJECT_DIR, "assistant.gif")
    vector_db_file: str = os.path.join(PROJECT_DIR, "data", "vector_db.json")
    chroma_db_dir: str = os.path.join(PROJECT_DIR, ".chroma")
    gold_data_file: str = os.path.join(PROJECT_DIR, "training", "arjun_gold_data.jsonl")

    def get_user_folder(self, folder_name: str) -> str:
        folder_name = folder_name.strip().lower()
        reg_keys = {
            "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
            "documents": "Personal",
            "desktop": "Desktop",
            "music": "My Music",
            "pictures": "My Pictures",
            "videos": "My Video"
        }
        
        if folder_name in reg_keys:
            reg_value = reg_keys[folder_name]
            try:
                import winreg
                sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    val, _ = winreg.QueryValueEx(key, reg_value)
                    resolved = os.path.expandvars(val)
                    if os.path.exists(resolved):
                        return resolved
            except Exception:
                pass
                
            try:
                import winreg
                sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    val, _ = winreg.QueryValueEx(key, reg_value)
                    if os.path.exists(val):
                        return val
            except Exception:
                pass

        # Fallback to standard locations on D, E, or C drive
        home_dir = os.path.expanduser("~")
        title_name = folder_name.title()
        if folder_name == "downloads":
            fallbacks = [
                r"D:\Downloads",
                r"E:\Downloads",
                os.path.join(home_dir, "Downloads")
            ]
        elif folder_name == "documents":
            fallbacks = [
                r"D:\Documents",
                r"E:\Documents",
                os.path.join(home_dir, "Documents")
            ]
        elif folder_name == "desktop":
            fallbacks = [
                r"D:\Desktop",
                r"E:\Desktop",
                os.path.join(home_dir, "Desktop")
            ]
        else:
            fallbacks = [
                os.path.join(home_dir, title_name)
            ]
            
        for path in fallbacks:
            if os.path.exists(path):
                return path
                
        return os.path.join(home_dir, title_name)

paths = Paths()
