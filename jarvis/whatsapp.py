
import re
import webbrowser
import urllib.parse
import sys
import os
import subprocess

CONTACTS = {
}

def parse_send_message_command(text: str):
    if not text:
        return None, None

    text = text.strip().lower()

    # Strip leading assistant names like "arjun", "jarvis", "hey arjun", "hey jarvis"
    text = re.sub(r"^(arjun|jarvis|hey arjun|hey jarvis)\s+", "", text).strip()

    # Pattern 1: Hinglish with "message karke poochho ki" / "message karke poochho" / "message karo ki" / "message karo"
    # Matches: [Name] ko message [karo/karke/poochho/karke poochho] [ki] [Message]
    hinglish_pattern = r"(.+?)\s+ko\s+message\s+(?:karo|karke\s+poochho|karke|poochho)\s+(?:ki\s+)?(.+)"
    m = re.match(hinglish_pattern, text)
    if m:
        contact_name = m.group(1).strip()
        message = m.group(2).strip()
        return contact_name, message

    # Pattern 2: Simple Hinglish [Name] ko message [Message] (without karo/ki)
    # Matches: [Name] ko message [Message]
    hinglish_simple = r"(.+?)\s+ko\s+message\s+(.+)"
    m = re.match(hinglish_simple, text)
    if m:
        contact_name = m.group(1).strip()
        message = m.group(2).strip()
        # Verify message doesn't start with keywords like "karo" or "ki"
        message = re.sub(r"^(karo|ki|karke|poochho)\s+", "", message).strip()
        return contact_name, message

    # Pattern 3: English - send (a) message to [Name] (saying/that/ki) [Message]
    english_pattern1 = r"(?:send\s+(?:a\s+)?)?message\s+to\s+([a-zA-Z0-9_]+)\s*(?:saying|that|ki)?\s+(.+)"
    m = re.match(english_pattern1, text)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Pattern 4: English - send [Name] a message (saying/that/ki) [Message]
    english_pattern2 = r"send\s+([a-zA-Z0-9_]+)\s+(?:a\s+)?message\s*(?:saying|that|ki)?\s+(.+)"
    m = re.match(english_pattern2, text)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Pattern 5: English - message [Name] [Message]
    english_pattern3 = r"message\s+(.+?)\s+(.+)"
    m = re.match(english_pattern3, text)
    if m:
        contact_name = m.group(1).strip()
        if contact_name in CONTACTS:
            return contact_name, m.group(2).strip()
        else:
            m2 = re.match(r"message\s+([a-zA-Z0-9_]+)\s*(?:saying|that|ki)?\s+(.+)", text)
            if m2:
                return m2.group(1).strip(), m2.group(2).strip()

    return None, None

def resolve_contact(name: str) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    return CONTACTS.get(key)

def _open_uri(uri: str):
    try:
        if sys.platform.startswith("win"):
            os.startfile(uri)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", uri])
        else:

            try:
                subprocess.Popen(["xdg-open", uri])
            except Exception:
                webbrowser.open(uri)
    except Exception:
        webbrowser.open(uri)

def open_whatsapp_app(phone: str, message: str):
    phone_clean = phone.replace("+", "").replace(" ", "")
    encoded_message = urllib.parse.quote(message)

    app_uri = f"whatsapp://send?phone={phone_clean}&text={encoded_message}"

    try:
        _open_uri(app_uri)
        return
    except Exception as e:
        print(f"WhatsApp app URI error: {e}")

    url = f"https://wa.me/{phone_clean}?text={encoded_message}"
    webbrowser.open(url)

def handle_whatsapp_command(text: str, audio_mgr, update_gui_status=None) -> bool:
    contact_name, message = parse_send_message_command(text)
    if not contact_name or not message:
        return False

    if update_gui_status:
        update_gui_status("Preparing WhatsApp message...")

    phone = resolve_contact(contact_name)
    if not phone:
        audio_mgr.say(
            f"I recognised this as a WhatsApp message command, "
            f"but I don't have a number saved for {contact_name}."
        )
        return True

    audio_mgr.say(
        f"Opening WhatsApp to message {contact_name}. "
        "Check the chat window and press Enter to send."
    )

    try:
        open_whatsapp_app(phone, message)
    except Exception as e:
        print(f"WhatsApp open error: {e}")
        audio_mgr.say("I had trouble opening WhatsApp.")
    return True
