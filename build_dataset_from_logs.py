# build_dataset_from_logs.py
"""
Build a fine-tuning dataset from Arjun/Jarvis episode logs.

It expects a JSONL log file where each line is a JSON object.
It tries to detect:
- user text  from keys like: query, user, user_input, prompt
- reply text from keys like: reply, response, assistant, assistant_reply, final_reply

Output: dataset.jsonl in chat format:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
"""

import json
import os
import argparse

CANDIDATE_USER_KEYS = [
    "query",
    "user",
    "user_input",
    "prompt",
    "question",
]

CANDIDATE_ASSIST_KEYS = [
    "assistant_reply",
    "reply",
    "response",
    "assistant",
    "final_reply",
    "answer",
]

try:
    # If you have jarvis.paths, use it for the default path
    from jarvis.paths import paths
    DEFAULT_LOG_PATH = paths.episode_log
except Exception:
    # Fallback: adjust this to your real log path if needed
    DEFAULT_LOG_PATH = "logs/episodes.jsonl"


CANDIDATE_USER_KEYS = [
    "query",
    "user",
    "user_input",
    "prompt",
    "question",
]

CANDIDATE_ASSIST_KEYS = [
    "assistant_reply",
    "reply",
    "response",
    "assistant",
    "final_reply",
    "answer",
]


def pick_first_str(d: dict, keys) -> str | None:
    """Return first non-empty string value for any of the given keys, or None."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str):
            v = v.strip()
            if v:
                return v
    return None


def build_dataset(
    log_path: str,
    out_path: str,
    max_examples: int | None = None,
    min_user_len: int = 4,
    min_assist_len: int = 4,
) -> None:
    if not os.path.exists(log_path):
        print(f"[ERROR] Log file not found: {log_path}")
        return

    total_lines = 0
    used_examples = 0
    skipped_no_json = 0
    skipped_missing_fields = 0

    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    with open(log_path, "r", encoding="utf-8") as fin, open(
        out_path, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            if max_examples is not None and used_examples >= max_examples:
                break

            total_lines += 1
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                skipped_no_json += 1
                continue

            user_text = pick_first_str(data, CANDIDATE_USER_KEYS)
            assist_text = pick_first_str(data, CANDIDATE_ASSIST_KEYS)

            if (
                not user_text
                or not assist_text
                or len(user_text) < min_user_len
                or len(assist_text) < min_assist_len
            ):
                skipped_missing_fields += 1
                continue

            example = {
                "messages": [
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": assist_text},
                ]
            }
            fout.write(json.dumps(example, ensure_ascii=False) + "\n")
            used_examples += 1

    print("=== Dataset build summary ===")
    print(f"Log file:           {log_path}")
    print(f"Output file:        {out_path}")
    print(f"Total log lines:    {total_lines}")
    print(f"Examples written:   {used_examples}")
    print(f"Skipped (no JSON):  {skipped_no_json}")
    print(f"Skipped (missing user/assistant text): {skipped_missing_fields}")


def main():
    parser = argparse.ArgumentParser(description="Build fine-tuning dataset from logs.")
    parser.add_argument(
        "--log",
        type=str,
        default=DEFAULT_LOG_PATH,
        help=f"Path to JSONL episode log (default: {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/dataset.jsonl",
        help="Output dataset path (JSONL).",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Optional limit on number of examples.",
    )
    parser.add_argument(
        "--min-user-len",
        type=int,
        default=4,
        help="Minimum user text length (chars) to keep an example.",
    )
    parser.add_argument(
        "--min-assist-len",
        type=int,
        default=4,
        help="Minimum assistant text length (chars) to keep an example.",
    )

    args = parser.parse_args()
    build_dataset(
        log_path=args.log,
        out_path=args.out,
        max_examples=args.max_examples,
        min_user_len=args.min_user_len,
        min_assist_len=args.min_assist_len,
    )


if __name__ == "__main__":
    main()
