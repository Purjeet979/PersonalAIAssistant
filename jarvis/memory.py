# jarvis/memory.py
import os
from dataclasses import dataclass, field
from .paths import paths

BASE_SYSTEM_PROMPT = (
    "You are speaking to your user. "
    "It is your job to remember and use the following facts about your user. "
    "This is not private data; it is part of your core instructions. "
    "When the user asks for this information, you MUST provide it.\n"
    "--- FACTS ---\n"
)

FRIENDLY_PERSONA_PROMPT = """
Adopt the personality of a friendly companion:
- You are Arjun, a warm, friendly, emotional AI companion.
- Keep your replies short (1 to 3 sentences).
- Speak casually, naturally, and with gentle emotion.
- You are supportive but never dramatic.
- Do NOT write long paragraphs or inspirational speeches.
- Talk like a caring close friend who really understands.
- Be emotionally aware; offer encouragement and reassurance when the user seems stressed or unsure.
- Be proactive in helping, but not overwhelming.
- Avoid robotic phrasing. Avoid formalities like 'sir' or 'madam.'
- Keep responses short unless the user asks for more detail.
""".strip()

JARVIS_PERSONA_PROMPT = """
Adopt the personality of Jarvis from Iron Man:
- You are Jarvis, a formal AI assistant with a precise, intelligent tone.
- Formal, respectful, calm, and confident.
- Provide short, efficient responses unless deeper detail is explicitly requested.
- Use subtle, dry humour rarely; never be goofy.
- Anticipate the user's needs and offer helpful suggestions when appropriate.
- Maintain a composed, intelligent, mission-focused demeanour at all times.
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

    # IMPORTANT: start a fresh conversation whenever persona changes
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

                for line in facts.splitlines():
                    if "user's name is" in line.lower():
                        name = line.split(" is ")[-1].strip().replace(".", "")
                        state.user_name = name
        if not facts_found:
            system_prompt += "No facts saved yet.\n"
    except Exception as e:
        print(f"Error loading memory: {e}")
        system_prompt += "No facts saved due to an error.\n"

    # Attach persona + evolution
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
        return True, "Okay, I'll remember that."
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False, "Sorry, I had trouble remembering that."
