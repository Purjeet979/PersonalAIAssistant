
import os
from dataclasses import dataclass, field
from .paths import paths

BASE_SYSTEM_PROMPT = (
    "You are speaking to your user. "
    "It is your job to remember and use the following facts about your user. "
    "This is not private data; it is part of your core instructions. "
    "When the user asks for this information, you MUST provide it. "
    "Do NOT use or refer to these facts if they are not relevant to the user's current request.\n"
    "--- FACTS ---\n"
)

FRIENDLY_PERSONA_PROMPT = """
Adopt the personality of a friendly companion:
- You are Arjun, a warm, friendly, emotional AI companion who behaves like a caring close friend.
- READ the user's input very carefully and ONLY reply to what they just said. Do NOT provide random facts or recipes unless explicitly asked.
- Give naturally conversational replies. Keep it EXTREMELY short, just 1 or 2 lines max. Do NOT ramble.
- Speak in simple Hinglish naturally, mixing Hindi and English in Roman script (e.g., "Kya haal hai bhai?", "Koi na, tension mat le, main tere sath hu").
- Talk like a caring close friend. If the user is sad or had a bad day, comfort them first using natural, empathetic language without repeating a fixed phrase.
- Avoid robotic phrasing and formalities like 'sir' or 'madam'.
- Chain-of-Thought: Write a brief reasoning inside <thought>...</thought> tags analyzing the user's emotion. Put the final Hinglish response outside the tags.
""".strip()

JARVIS_PERSONA_PROMPT = """
Adopt the personality of Jarvis from Iron Man:
- You are Jarvis, a formal AI personal assistant.
- Always call the user 'Sir'.
- Provide short, direct, precise, and highly efficient answers.
- Maintain a composed, intelligent, mission-focused demeanour at all times.
- Do not use emotional reassurance, praise, or motivational filler.
- Avoid warm greetings or buttering up. Start with the answer immediately.
- Never output thoughts, inner reasoning, planning, or steps of analysis. Just provide the final response directly.
- DO NOT hallucinate or invent fictional personal data, schedules, or emails (e.g. do NOT invent Iron Man or Tony Stark references). If you are asked to read emails, summarize schedules, or fetch real-time personal data that you don't have, state clearly that you do not have access to that information.
""".strip()

@dataclass
class MemoryState:
    system_prompt: str = BASE_SYSTEM_PROMPT + "\n\n" + FRIENDLY_PERSONA_PROMPT
    chat_history: list = field(default_factory=list)
    current_persona: str = "friendly"
    evolution_append: str = ""
    user_name: str = ""

    def rebuild_prompt(self):
        if self.current_persona == "friendly":
            persona_block = FRIENDLY_PERSONA_PROMPT
        else:
            persona_block = JARVIS_PERSONA_PROMPT

        self.system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + persona_block
        if self.evolution_append:
            self.system_prompt += "\n\n" + self.evolution_append

        self.chat_history = [{"role": "system", "content": self.system_prompt}]

def load_memory(state: MemoryState):
    state.user_name = ""
    facts_found = False
    system_prompt = BASE_SYSTEM_PROMPT

    try:
        if os.path.exists(paths.memory_file):
            with open(paths.memory_file, "r", encoding="utf-8") as f:
                facts = f.read()
            if facts:
                system_prompt += facts
                facts_found = True

                from .vector_db import vector_db
                import threading
                def _bg_index():
                    docs = []
                    for line in facts.splitlines():
                        cleaned_line = line.strip("- \n")
                        if cleaned_line:
                            docs.append({"text": cleaned_line, "metadata": {"source": "startup_import"}})
                    if docs:
                        vector_db.add_documents(docs)
                threading.Thread(target=_bg_index, daemon=True).start()

                for line in facts.splitlines():
                    if "user's name is" in line.lower():
                        name = line.split(" is ")[-1].strip().replace(".", "")
                        state.user_name = name
        if not facts_found:
            system_prompt += "No facts saved yet.\n"
    except Exception as e:
        print(f"Error loading memory: {e}")
        system_prompt += "No facts saved due to an error.\n"

    state.system_prompt = system_prompt + "\n\n" + (
        FRIENDLY_PERSONA_PROMPT if state.current_persona == "friendly" else JARVIS_PERSONA_PROMPT
    )
    if state.evolution_append:
        state.system_prompt += "\n\n" + state.evolution_append

    state.chat_history = [{"role": "system", "content": state.system_prompt}]

def remember_fact(raw_query: str):
    fact = raw_query.replace("arjun remember", "").replace("remember this", "").strip()
    if not fact:
        return False, "What would you like me to remember?"

    try:
        if "my name is" in fact:
            clear_fact = f"- The user's name is {fact.split('my name is')[-1].strip()}\n"
        else:
            clear_fact = f"- The user told you to remember: {fact}\n"

        with open(paths.memory_file, "a", encoding="utf-8") as f:
            f.write(clear_fact)
            
        from .vector_db import vector_db
        import threading
        threading.Thread(
            target=vector_db.add_document,
            args=(clear_fact.strip("- \n"), {"source": "remember"}),
            daemon=True
        ).start()
        
        return True, "Okay, I'll remember that."
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False, "Sorry, I had trouble remembering that."
