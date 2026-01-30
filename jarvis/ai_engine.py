# jarvis/ai_engine.py
import os
import json
import time
import wikipedia
import re
import ollama
from .paths import paths
from .memory import MemoryState
from jarvis.logger import log_episode

# --- SETTINGS ---
MAX_HISTORY_LIMIT = 20  # Keep only last 20 messages to prevent confusion

def apply_persona_style(reply: str, state: MemoryState) -> str:
    reply = reply.strip()
    if state.current_persona == "jarvis":
        if not reply.lower().startswith("sir"):
            reply = "Sir, " + reply[0].lower() + reply[1:]
        return reply

    stiff_prefixes = ["Dear sir", "Greetings", "Hello sir"]
    for p in stiff_prefixes:
        if reply.lower().startswith(p.lower()):
            reply = reply[len(p):].lstrip(" ,.")
            break
    return reply

def chat(query: str, state: MemoryState, say, update_gui_status):
    update_gui_status("Thinking...")

    # 1. HANDLE WIKIPEDIA SEARCHES
    knowledge_triggers = ["who is", "what is", "tell me about", "why is", "how does"]
    is_knowledge = any(t in query.lower() for t in knowledge_triggers) and "my" not in query.lower()

    knowledge_context = ""
    if is_knowledge:
        topic = (
            query.lower()
            .replace("who is", "")
            .replace("what is", "")
            .replace("tell me about", "")
            .replace("hey arjun", "")
            .strip()
        )
        
        # --- FIX: DON'T LET HIM GOOGLE HIMSELF ---
        if topic and topic != "arjun": 
            try:
                update_gui_status(f"Searching Wikipedia for {topic}...")
                summary = wikipedia.summary(topic, sentences=2)
                knowledge_context = f"\n\n[Context: {summary}]"
                say(f"I found this on Wikipedia about {topic}.")
            except Exception:
                pass # Silent fail is better than crashing
        # -----------------------------------------

    full_query = f"{query}{knowledge_context}"

    # 2. MANAGE HISTORY (Prevent infinite growth)
    if not state.chat_history:
        state.chat_history.append({"role": "system", "content": state.system_prompt})
    
    # Keep system prompt + last N messages
    if len(state.chat_history) > MAX_HISTORY_LIMIT:
        state.chat_history = [state.chat_history[0]] + state.chat_history[-(MAX_HISTORY_LIMIT-1):]

    state.chat_history.append({"role": "user", "content": full_query})

    # 3. SELECT BRAIN
    if state.current_persona == "friendly":
        model_name = "arjun-custom"
    else:
        model_name = "gemma:2b"

    try:
        resp = ollama.chat(model=model_name, messages=state.chat_history,keep_alive="60m")
        reply = resp["message"]["content"].strip()
        
        # Cleanup response
        reply = apply_persona_style(reply, state)
        
        say(reply)
        state.chat_history.append({"role": "assistant", "content": reply})
        log_episode(query, reply, "chat", True)

    except Exception as e:
        print(f"Ollama chat error: {e}")
        say("I'm having trouble connecting to my brain.")
        log_episode(query, "", "chat", False, str(e))

# ... (Keep ai_generate and self_evaluate_and_improve exactly as they were) ...
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
            lines = f.readlines()[-50:]
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