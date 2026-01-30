# jarvis/paths.py
import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # /JarvisAI/jarvis
PROJECT_DIR = os.path.dirname(BASE_DIR)                # /JarvisAI

@dataclass
class Paths:
    # --- ADD THIS NEW LINE BELOW ---
    PROJECT_DIR: str = PROJECT_DIR  
    # -------------------------------
    
    memory_file: str = os.path.join(PROJECT_DIR, "arjun_memory.txt")
    commands_file: str = os.path.join(PROJECT_DIR, "custom_commands.json")
    notes_file: str = os.path.join(PROJECT_DIR, "notes.txt")
    episode_log: str = os.path.join(PROJECT_DIR, "episodes.jsonl")
    improvements_file: str = os.path.join(PROJECT_DIR, "improvements.txt")
    openai_dir: str = os.path.join(PROJECT_DIR, "Openai")
    assistant_gif: str = os.path.join(PROJECT_DIR, "assistant.gif")

paths = Paths()