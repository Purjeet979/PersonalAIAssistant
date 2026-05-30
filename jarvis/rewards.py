import json
import os
import time
from .paths import paths

def log_feedback(query: str, reply: str, rating: str) -> bool:
    """
    Log user-assistant interaction with human feedback rating (good/bad).
    Saves to the gold standard dataset JSONL file.
    """
    query = (query or "").strip()
    reply = (reply or "").strip()
    rating = (rating or "").strip().lower()

    if not query or not reply:
        print("[RLHF] Empty query or reply, skipping feedback log.")
        return False

    if rating not in ("good", "bad"):
        print(f"[RLHF] Invalid rating '{rating}', skipping feedback log.")
        return False

    # Construct standard fine-tuning format
    record = {
        "ts": time.time(),
        "query": query,
        "assistant_reply": reply,
        "rating": rating
    }

    try:
        # Ensure training directory exists
        out_dir = os.path.dirname(paths.gold_data_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(paths.gold_data_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        print(f"[RLHF] Successfully logged '{rating}' feedback for query: '{query[:30]}...'")
        return True
    except Exception as e:
        print(f"[RLHF] Error logging feedback to file: {e}")
        return False
