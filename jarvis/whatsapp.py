# jarvis/whatsapp.py
import re
import webbrowser
import urllib.parse
import sys
import os
import subprocess


# Keys are how you will say the name in speech (lowercase).
CONTACTS = {
    "surya": "+919823711834",   
    "didi": "+918329675587",
    "mummy": "+919923499314",
    "papa": "+919158990179"
}



def parse_send_message_command(text: str):
    """
    Parse Hinglish-style commands like:
      'didi ko message karo ki kal main nahi aunga'
      'mummy ko message karo ki main late aunga'
      'mummy ko message karke pucho ki app kya kar rahe ho'
    Returns: (contact_name, message) or (None, None)
    """
    if not text:
        return None, None

    text = text.strip().lower()

    # pattern: <name> ko message karo ki <msg>
    pattern = r"(.+?)\s+ko\s+message\s+karo\s+ki\s+(.+)"
    m = re.match(pattern, text)
    if not m:
        return None, None

    contact_name = m.group(1).strip()
    message = m.group(2).strip()
    if not contact_name or not message:
        return None, None

    return contact_name, message


def resolve_contact(name: str) -> str | None:
    """Return phone number for a contact name, or None if not configured."""
    if not name:
        return None
    key = name.strip().lower()
    return CONTACTS.get(key)


def _open_uri(uri: str):
    """
    Open a URI using the OS default handler.
    On Windows: os.startfile
    On macOS/Linux: fall back to webbrowser / xdg-open / open.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(uri)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", uri])
        else:
            # Linux etc.
            try:
                subprocess.Popen(["xdg-open", uri])
            except Exception:
                webbrowser.open(uri)
    except Exception:
        webbrowser.open(uri)


def open_whatsapp_app(phone: str, message: str):
    """
    Try to open WhatsApp Desktop using the whatsapp:// URI scheme.
    Falls back to wa.me in browser if needed.
    """
    phone_clean = phone.replace("+", "").replace(" ", "")
    encoded_message = urllib.parse.quote(message)

    # 1) Try direct app scheme
    app_uri = f"whatsapp://send?phone={phone_clean}&text={encoded_message}"

    try:
        _open_uri(app_uri)
        return
    except Exception as e:
        print(f"WhatsApp app URI error: {e}")

    # 2) Fallback: wa.me (web)
    url = f"https://wa.me/{phone_clean}?text={encoded_message}"
    webbrowser.open(url)


def handle_whatsapp_command(text: str, audio_mgr, update_gui_status=None) -> bool:
    """
    High-level handler.
    - Returns True if this was a WhatsApp command (handled or failed).
    - Returns False if the text is not a WhatsApp command (let normal AI handle it).
    """
    contact_name, message = parse_send_message_command(text)
    if not contact_name or not message:
        return False  # not our pattern

    if update_gui_status:
        update_gui_status("Preparing WhatsApp message...")

    phone = resolve_contact(contact_name)
    if not phone:
        audio_mgr.say(
            f"I recognised this as a WhatsApp message command, "
            f"but I don't have a number saved for {contact_name}."
        )
        return True  # pattern matched, but cannot complete

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
