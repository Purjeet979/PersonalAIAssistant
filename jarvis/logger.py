# jarvis/logger.py
import json
import time
from jarvis.paths import paths


def log_episode(query: str,
                reply: str,
                handler: str,
                success: bool,
                notes: str = "") -> None:
    """
    Append a single interaction to episodes.jsonl for future fine-tuning.

    query   = user's text
    reply   = assistant's final reply text (can be "" on error)
    handler = which module handled it, e.g. "chat", "weather"
    success = True/False
    notes   = optional error / extra info
    """
    record = {
        "ts": time.time(),
        "query": query,
        "assistant_reply": reply,
        "handler": handler,
        "success": success,
        "notes": notes,
    }

    try:
        with open(paths.episode_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Log write error: {e}")
