
import os
import json
import time
import warnings
import wikipedia
import re
import ollama
from collections import deque
from .paths import paths
from .memory import MemoryState
from jarvis.logger import log_episode

try:
    from bs4 import GuessedAtParserWarning
    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
except Exception:
    pass

MAX_HISTORY_LIMIT = 20
KNOWLEDGE_TRIGGERS = ("who is", "what is", "tell me about", "why is", "how does")
STIFF_PREFIXES = ("Dear sir", "Greetings", "Hello sir")
PERSONA_MODELS = {"friendly": "arjun-custom", "jarvis": "gemma:2b"}
FRIENDLY_CHAT_OPTIONS = {"temperature": 0.55, "top_p": 0.92, "num_predict": 260}
JARVIS_CHAT_OPTIONS = {"temperature": 0.2, "top_p": 0.85, "num_predict": 180}
EMOTIONAL_CUES = ("sad", "stress", "stressed", "low", "anxious", "anxiety", "upset", "tired", "lonely", "hurt", "depressed", "bad day")
ONE_WORD_ALLOW = ("one word", "single word", "just one word", "yes or no", "only yes or no")
SHORT_REPLY_MAX_WORDS = 4
RECIPE_CUES = ("recipe", "how to make", "make", "cook", "cooking", "sandwich", "anda", "egg")
GENERIC_REPLY_CUES = ("i will", "with you", "sure", "okay", "ok", "done", "let's do it", "ill do it", "i'll do it")
JARVIS_FLUFF_PREFIXES = (
    "absolutely",
    "certainly",
    "of course",
    "great question",
    "that's a great question",
    "i'd be happy to",
    "sure",
)
JARVIS_FLUFF_PHRASES = (
    "that is a great question",
    "i hope this helps",
    "let me know if you need anything else",
    "if you want, i can",
    "feel free to ask",
)

def _trim_history(history):
    if len(history) <= MAX_HISTORY_LIMIT:
        return history
    return [history[0]] + history[-(MAX_HISTORY_LIMIT - 1):]

def _sanitize_query(query: str):
    q = (query or "").strip()
    ql = q.lower()
    for w in ("hey arjun", "arjun", "hey jarvis", "jarvis"):
        if ql.startswith(w):
            q = q[len(w):].strip(" ,.-")
            ql = q.lower()
            break
    return (q or query).strip(), (q or query).strip().lower()

def _knowledge_context(query: str, query_lower: str, say, update_gui_status) -> str:
    if not any(t in query_lower for t in KNOWLEDGE_TRIGGERS) or "my" in query_lower:
        return ""
    topic = query_lower.replace("who is", "").replace("what is", "").replace("tell me about", "").replace("hey arjun", "").strip()
    if not topic or topic == "arjun":
        return ""
    try:
        update_gui_status(f"Searching Wikipedia for {topic}...")
        summary = wikipedia.summary(topic, sentences=2)
        say(f"I found this on Wikipedia about {topic}.")
        return f"\n\n[Context: {summary}]"
    except Exception:
        return ""

def apply_persona_style(reply: str, state: MemoryState) -> str:
    reply = reply.strip()
    if not reply:
        return reply
    if state.current_persona == "jarvis":
        low = reply.lower().strip()
        for p in JARVIS_FLUFF_PREFIXES:
            if low.startswith(p):
                reply = re.sub(r"^[^,.!?]*[,.!?]\s*", "", reply).strip() or reply
                low = reply.lower().strip()
                break
        for p in JARVIS_FLUFF_PHRASES:
            reply = re.sub(rf"\b{re.escape(p)}\b[,.!?\s]*", "", reply, flags=re.IGNORECASE)
            low = reply.lower().strip()
        reply = re.sub(r"\s+", " ", reply).strip()
        if not reply:
            reply = "Done."
        if reply[-1] not in ".!?":
            reply += "."
        if not reply.lower().startswith("sir"):
            reply = "Sir, " + reply[0].lower() + reply[1:]
        return reply

    for p in STIFF_PREFIXES:
        if reply.lower().startswith(p.lower()):
            reply = reply[len(p):].lstrip(" ,.")
            break
    reply = re.sub(r"^(sir|madam|dear)\b[,:\s-]*", "", reply, flags=re.IGNORECASE).strip()
    return reply

def _enrich_friendly_reply(query_lower: str, reply: str) -> str:
    words = len(reply.split())
    is_recipe_query = any(c in query_lower for c in RECIPE_CUES)
    generic_reply = reply.lower().strip()
    looks_generic = any(g in generic_reply for g in GENERIC_REPLY_CUES)

    if is_recipe_query and (words < 30 or looks_generic):
        return (
            "Perfect, egg sandwich banate hain. Quick recipe: 1) 2 ande bowl me todkar namak, kali mirch, thoda chopped pyaz mirchi mix karo. "
            "2) Pan me thoda butter daalke mixture ko scramble ya omelette style paka lo. "
            "3) 2 bread slices ko butter ke sath light toast karo. "
            "4) Bread par mayo ya chutney lagao, egg filling rakho, chahe to cheese/tomato add karo, phir close karke 1 minute press-toast karo. "
            "5) Half cut karke garam serve karo. Chahe to main spicy ya healthy version bhi bata du."
        )

    if words > 10:
        return reply
    if any(k in query_lower for k in ONE_WORD_ALLOW):
        return reply
    if not any(c in query_lower for c in EMOTIONAL_CUES):
        if words > SHORT_REPLY_MAX_WORDS:
            return reply
        tail = "Tu chahe to main thoda detail me samjha du ya next step bata du?"
        if any(x in query_lower for x in ("what", "why", "how", "kaise", "kya", "kyu", "explain")):
            tail = "Agar bole to main isko simple aur clear way me step-by-step explain kar deta hu."
        elif any(x in query_lower for x in ("plan", "career", "job", "study", "exam", "project", "help")):
            tail = "Chal isko easy banate hain, main abhi 2-3 practical steps de deta hu."
        if reply and reply[-1] not in ".!?":
            reply += "."
        return f"{reply} {tail}"
    if reply and reply[-1] not in ".!?":
        reply += "."
    return f"{reply} Koi na, main tere sath hu, I will support you. Tu chahe to bata kya hua, ya main abhi ek chhota next step suggest kar du?"

def chat(query: str, state: MemoryState, say, update_gui_status):
    update_gui_status("Thinking...")

    query, query_lower = _sanitize_query(query)
    knowledge_context = _knowledge_context(query, query_lower, say, update_gui_status)

    full_query = f"{query}{knowledge_context}"

    if not state.chat_history:
        state.chat_history.append({"role": "system", "content": state.system_prompt})

    state.chat_history = _trim_history(state.chat_history)
    if len(state.chat_history) > 8:
        state.chat_history = [state.chat_history[0]] + state.chat_history[-7:]

    state.chat_history.append({"role": "user", "content": full_query})

    model_name = PERSONA_MODELS.get(state.current_persona, "arjun-custom")
    chat_options = FRIENDLY_CHAT_OPTIONS if state.current_persona == "friendly" else JARVIS_CHAT_OPTIONS

    try:
        resp = ollama.chat(model=model_name, messages=state.chat_history, keep_alive="60m", options=chat_options)
        reply = resp["message"]["content"].strip()

        reply = apply_persona_style(reply, state)
        if state.current_persona == "friendly":
            reply = _enrich_friendly_reply(query_lower, reply)

        say(reply)
        state.chat_history.append({"role": "assistant", "content": reply})
        log_episode(query, reply, "chat", True)

    except Exception as e:
        print(f"Ollama chat error: {e}")
        say("I'm having trouble connecting to my brain.")
        log_episode(query, "", "chat", False, str(e))

def ai_generate(prompt: str, state: MemoryState, say, update_gui_status, speak_result=False):
    update_gui_status("Generating...")
    full_prompt = f"{state.system_prompt}\n\nUser's request: {prompt}"

    try:
        resp = ollama.generate(model="gemma:2b", prompt=full_prompt)
        text = resp["response"]

        if speak_result:
            text = apply_persona_style(text, state)
            say(text)
        else:
            os.makedirs(paths.openai_dir, exist_ok=True)
            fname = f"{prompt[0:30].replace(' ', '_')}-{time.strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(paths.openai_dir, fname)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Prompt: {prompt}\n\nResponse:\n{text}")
            say("I have generated a response and saved it to a file.")
    except Exception as e:
        print(f"Ollama generate error: {e}")
        say("I'm having trouble connecting to my local AI brain. Is Ollama running?")

def self_evaluate_and_improve(state: MemoryState, say):
    import json
    import os

    if not os.path.exists(paths.episode_log):
        say("I have no interaction history to learn from yet.")
        return

    try:
        with open(paths.episode_log, "r", encoding="utf-8") as f:
            lines = deque(f, maxlen=50)
    except Exception as e:
        print(f"Read log error: {e}")
        say("I had trouble reading my logs.")
        return

    episodes_text = "".join(lines)

    improve_prompt = """You are Arjun's self-improvement module.

Chat in a natural way. Do not use Sir often. Have a normal conversation like a friend.
Below are recent interaction logs in JSONL format. Each line has: query, handler, success, and notes.

1. Briefly summarize any recurring problems, user frustrations, or obvious misunderstandings.
2. Propose:
   - New trigger phrases that should map to EXISTING handler names I already use.
   - Optional extra instructions to append to my system prompt to better match the user's preferences.
3. Only use handlers that sound generic (like 'chat', 'weather_builtin', 'notes_add', 'media_playpause', etc.).
4. DO NOT propose new arbitrary Python code.

Respond ONLY in this strict JSON format (no extra commentary, no markdown):

{
  "new_triggers": [
    {"trigger": "phrase user says", "handler": "existing_handler_name", "reason": "why this helps"}
  ],
  "system_prompt_append": "extra natural-language instructions to append to the current prompt or empty string"
}
"""

    try:
        resp = ollama.generate(
            model="llama3:8b",
            prompt=improve_prompt + "\n\nLOGS:\n" + episodes_text
        )
        raw = (resp.get("response") or "").strip()
    except Exception as e:
        print(f"Self-evolution LLM error: {e}")
        say("I had trouble accessing my local AI brain for self-improvement.")
        return

    if not raw:
        say("I tried to improve myself but got an empty response from my local model.")
        return

    suggestions = None
    try:
        suggestions = json.loads(raw)
    except Exception as e1:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                suggestions = json.loads(candidate)
            except Exception as e2:
                print(f"JSON parse error (second attempt): {e2}")
        else:
            print(f"JSON parse error: {e1}")

    if suggestions is None:
        say("I tried to improve myself but the suggestions were not valid JSON.")
        return

    sp_append = (suggestions.get("system_prompt_append") or "").strip()
    if sp_append:
        if state.evolution_append:
            state.evolution_append += "\n\n" + sp_append
        else:
            state.evolution_append = sp_append

        state.rebuild_prompt()
        try:
            with open(paths.improvements_file, "a", encoding="utf-8") as f:
                f.write("SYSTEM_PROMPT_APPEND:\n" + sp_append + "\n\n")
        except Exception as e:
            print(f"Improvement file error: {e}")

    say("I have reviewed my recent interactions and updated some of my internal settings to improve future responses.")
