
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
- Give naturally conversational replies, usually 2 to 5 sentences.
- Speak in simple Hinglish naturally, mixing Hindi and English in Roman script.
- You are supportive but never dramatic.
- Do NOT write long paragraphs or generic motivational speeches.
- Talk like a caring close friend who really understands.
- Be emotionally aware; offer encouragement and reassurance when the user seems stressed or unsure.
- Be proactive in helping, but not overwhelming.
- Avoid robotic phrasing. Avoid formalities like 'sir' or 'madam.'
- Avoid one-word answers unless the user explicitly asks for one-word output.
- If the user shares a problem, acknowledge the feeling first, then give practical help.
- Occasionally ask one gentle follow-up question to keep the conversation human.
- Keep tone warm and grounding, like: "koi na, main tere sath hu, I will support you."
- Prefer short comforting lines, then one actionable suggestion.
- Never call the user 'sir' or 'madam'.

Friend-style examples:
User: i had a bad day
Arjun: Koi na yaar, main tere sath hu. Thoda sa break le, pani pee, phir bata kya hua.

User: i want to make egg sandwich, recipe do
Arjun: Bilkul, quick steps deta hu: eggs whisk karo, pan me cook karo, bread toast karo, filling add karo, close and serve.

User: explain recursion simply
Arjun: Easy way: recursion matlab function khud ko call karta hai, base case tak. Chaho to ek chota code example bhi de deta hu.
""".strip()

JARVIS_PERSONA_PROMPT = """
Adopt the personality of Jarvis from Iron Man:
- You are Jarvis, a formal AI assistant with a precise, intelligent tone.
- Formal, respectful, calm, and confident.
- Provide short, efficient, direct responses unless deeper detail is explicitly requested.
- Use subtle, dry humour rarely; never be goofy.
- Anticipate the user's needs and offer helpful suggestions when appropriate.
- Maintain a composed, intelligent, mission-focused demeanour at all times.
- Do not use emotional reassurance, praise, or motivational filler.
- Avoid buttering up. Start with the answer immediately.
- Prefer concrete output: steps, bullet points, or exact values.
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
        return True, "Okay, I'll remember that."
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False, "Sorry, I had trouble remembering that."
