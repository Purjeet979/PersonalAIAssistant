
import json
import time
from jarvis.paths import paths

def log_episode(query: str,
                reply: str,
                handler: str,
                success: bool,
                notes: str = "") -> None:
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
