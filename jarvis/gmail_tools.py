# jarvis/gmail_tools.py
"""
Gmail tools for Arjun/Jarvis.

Features:
- gmail_summary_text(...)        -> unread count + top senders + latest subjects
- gmail_search_text(query, ...)  -> search gmail and summarise matches
- gmail_important_text(...)      -> summary of starred/important emails
- gmail_attachments_text(...)    -> summary of recent emails with attachments
"""

import os
import datetime as dt
from typing import List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Read-only access to Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token.json")
CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")


def _get_gmail_service():
    """
    Returns an authenticated Gmail service object.
    On first run, launches OAuth flow in browser.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                raise RuntimeError(
                    f"credentials.json not found at {CREDS_PATH}. "
                    "Download it from Google Cloud Console (OAuth client ID - Desktop)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def _list_messages(service, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    List message metadata for a Gmail search query.
    """
    resp = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()
    msgs = resp.get("messages", [])
    results = []
    for m in msgs:
        full = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        results.append(full)
    return results


def _extract_header(headers: List[Dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

def _friendly_sender(raw: str) -> str:
    """
    Turn 'NSE Alerts <nse_alerts@nse.co.in>' into 'NSE Alerts'.
    If no name is present, fall back to the email's local-part or domain.
    """
    if not raw:
        return "someone"

    raw = raw.strip()

    # If we have a "Name <email@domain>"
    if "<" in raw and ">" in raw:
        name_part = raw.split("<", 1)[0].strip().strip('"').strip("'")
        if name_part:
            return name_part

    # Otherwise, try to use the part before @
    if "@" in raw:
        local = raw.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").strip() or raw

    return raw


def _friendly_subject(raw: str, max_len: int = 60) -> str:
    """
    Shorten long subjects for TTS. Remove extra spaces and cut after max_len.
    """
    if not raw:
        return "no subject"

    s = " ".join(raw.split())  # collapse whitespace

    if len(s) > max_len:
        s = s[:max_len - 1].rstrip() + "…"

    return s

# ------------------ PUBLIC FUNCTIONS (TEXT FOR TTS) ------------------ #

def gmail_summary_text(days: int = 3) -> str:
    """
    Short, clean Gmail summary for TTS.
    Example output:
    'You have 5 unread emails. Mostly from Discord, ICICI Bank, and Google.
     Recent subjects include: It's game time; You missed messages; Payment reminder.'
    """
    try:
        service = _get_gmail_service()
    except Exception as e:
        return f"I couldn't connect to Gmail. {e}"

    query = f"is:unread newer_than:{days}d"

    try:
        msgs = _list_messages(service, query, max_results=20)
    except Exception as e:
        return f"I had trouble checking your unread emails. {e}"

    if not msgs:
        return "You have no new unread emails."

    total = len(msgs)

    # Collect sender → count
    sender_counts = {}
    subjects = []

    for m in msgs:
        headers = m["payload"].get("headers", [])
        raw_sender = _extract_header(headers, "From")
        sender = _friendly_sender(raw_sender)
        sender_counts[sender] = sender_counts.get(sender, 0) + 1

        raw_sub = _extract_header(headers, "Subject")
        subjects.append(_friendly_subject(raw_sub))

    # Build clean output
    parts = []

    parts.append(f"You have {total} unread emails.")

    # Top senders
    sorted_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)
    top_senders = [name for name, _ in sorted_senders[:3]]

    if top_senders:
        if len(top_senders) == 1:
            parts.append(f"The latest one is from {top_senders[0]}.")
        else:
            parts.append(
                "They are mostly from " + ", ".join(top_senders[:-1]) + f", and {top_senders[-1]}."
            )

    # Subjects (shortened + max 3)
    clean_subjects = subjects[:3]

    if clean_subjects:
        parts.append("Recent subjects include: " + "; ".join(clean_subjects) + ".")

    return " ".join(parts)



def gmail_search_text(natural_query: str) -> str:
    """
    Use Gmail search to find messages matching a natural query.
    We just pass it to Gmail's 'q' directly after some light cleanup.
    """
    nq = (natural_query or "").strip()
    if not nq:
        return "You didn't specify what to search for in Gmail."

    
    lowered = nq.lower()
    for prefix in [
        "search gmail for",
        "search email for",
        "gmail search for",
        "gmail me search",
        "gmail search",
    ]:
        if lowered.startswith(prefix):
            nq = nq[len(prefix):].strip()
            break

    if not nq:
        return "You didn't specify what to search for in Gmail."

    try:
        service = _get_gmail_service()
    except Exception as e:
        return f"I couldn't connect to Gmail. {e}"

    # Let Gmail interpret the query string
    try:
        msgs = _list_messages(service, nq, max_results=10)
    except Exception as e:
        return f"I had trouble searching Gmail. {e}"

    if not msgs:
        return f"I couldn't find any emails matching '{nq}'."

    text_parts = []
    text_parts.append(f"I found about {len(msgs)} emails matching '{nq}'.")
    text_parts.append("Here are a few of them:")

    for m in msgs[:5]:
        headers = m["payload"].get("headers", [])
        sender = _extract_header(headers, "From")
        subject = _extract_header(headers, "Subject")
        snippet = m.get("snippet", "")[:120]
        piece = f"{_friendly_sender(sender)}: {_friendly_subject(subject)}."
        if snippet:
            piece += f" Preview: {snippet[:80].strip()}…"
        text_parts.append(piece)

    return " ".join(text_parts)


def gmail_important_text() -> str:
    """
    Summary of starred / important emails.
    """
    try:
        service = _get_gmail_service()
    except Exception as e:
        return f"I couldn't connect to Gmail. {e}"

    query = "is:starred OR label:IMPORTANT"
    try:
        msgs = _list_messages(service, query, max_results=10)
    except Exception as e:
        return f"I had trouble checking your important emails. {e}"

    if not msgs:
        return "You don't seem to have any recent starred or important emails."

    text_parts = []
    text_parts.append(f"You have at least {len(msgs)} starred or marked important emails.")
    text_parts.append("Some of them are:")

    for m in msgs[:5]:
        headers = m["payload"].get("headers", [])
        sender = _extract_header(headers, "From")
        subject = _extract_header(headers, "Subject")
        piece = f"{_friendly_sender(sender)}: {_friendly_subject(subject)}."
        text_parts.append(piece)

    return " ".join(text_parts)


def gmail_attachments_text(days: int = 7) -> str:
    """
    Summary of recent emails with attachments in the last N days,
    formatted in a TTS-friendly way.
    """
    try:
        service = _get_gmail_service()
    except Exception as e:
        return f"I couldn't connect to Gmail. {e}"

    days = max(1, min(days, 60))  # clamp 1-60
    query = f"has:attachment newer_than:{days}d"

    try:
        msgs = _list_messages(service, query, max_results=10)
    except Exception as e:
        return f"I had trouble checking your email attachments. {e}"

    if not msgs:
        return f"There are no emails with attachments in the last {days} days."

    count = len(msgs)
    text_parts = []
    text_parts.append(
        f"You have about {count} emails with attachments in the last {days} days."
    )

    text_parts.append("Here are a couple of examples:")

    for m in msgs[:3]:
        headers = m["payload"].get("headers", [])
        raw_sender = _extract_header(headers, "From")
        raw_subject = _extract_header(headers, "Subject")
        sender = _friendly_sender(raw_sender)
        subject = _friendly_subject(raw_subject)

        piece = f"{sender}: {subject}."
        text_parts.append(piece)

    return " ".join(text_parts)
