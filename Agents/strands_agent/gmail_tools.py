import base64
import re
from datetime import datetime, timedelta

from strands import tool

from auth import get_gmail_service


def _get_header(headers: list, name: str) -> str:
    """Extract a header value by name from Gmail message headers."""
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]
    return ""


def _decode_body(payload: dict) -> str:
    """Decode the email body from a Gmail message payload."""
    body_text = ""

    if payload.get("body", {}).get("data"):
        body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    if not body_text and payload.get("parts"):
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
            elif mime == "text/html" and part.get("body", {}).get("data") and not body_text:
                raw_html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                body_text = re.sub(r"<[^>]+>", " ", raw_html)
                body_text = re.sub(r"\s+", " ", body_text).strip()
            elif mime.startswith("multipart/") and part.get("parts"):
                body_text = _decode_body(part)
                if body_text:
                    break

    return body_text[:3000]  # truncate to keep token usage reasonable


@tool
def fetch_recent_emails(days_back: int = 7, max_results: int = 50) -> str:
    """Fetch emails from Gmail received in the last N days.

    Returns a summary list of emails with id, subject, sender, date, and snippet.
    Use this to get an overview before fetching full details on specific emails.

    Args:
        days_back: Number of days to look back (default 7)
        max_results: Maximum number of emails to return (default 50)
    """
    service = get_gmail_service()
    after_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"after:{after_date}"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return "No emails found in the specified time period."

    email_summaries = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date", "List-Unsubscribe"]
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])
        labels = msg.get("labelIds", [])

        email_summaries.append({
            "id": msg["id"],
            "subject": _get_header(headers, "Subject"),
            "from": _get_header(headers, "From"),
            "to": _get_header(headers, "To"),
            "date": _get_header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "labels": labels,
            "has_unsubscribe": bool(_get_header(headers, "List-Unsubscribe")),
        })

    summary_lines = []
    for e in email_summaries:
        summary_lines.append(
            f"ID: {e['id']}\n"
            f"  From: {e['from']}\n"
            f"  To: {e['to']}\n"
            f"  Subject: {e['subject']}\n"
            f"  Date: {e['date']}\n"
            f"  Snippet: {e['snippet']}\n"
            f"  Labels: {', '.join(e['labels'])}\n"
            f"  Has Unsubscribe Header: {e['has_unsubscribe']}"
        )

    return f"Found {len(email_summaries)} emails:\n\n" + "\n\n".join(summary_lines)


@tool
def get_email_details(email_id: str) -> str:
    """Get the full details and body of a specific email by its ID.

    Use this after fetch_recent_emails to read the full content of emails
    that look like they may need attention.

    Args:
        email_id: The Gmail message ID to retrieve
    """
    service = get_gmail_service()

    msg = service.users().messages().get(
        userId="me", id=email_id, format="full"
    ).execute()

    headers = msg.get("payload", {}).get("headers", [])
    body = _decode_body(msg.get("payload", {}))

    return (
        f"From: {_get_header(headers, 'From')}\n"
        f"To: {_get_header(headers, 'To')}\n"
        f"CC: {_get_header(headers, 'Cc')}\n"
        f"Subject: {_get_header(headers, 'Subject')}\n"
        f"Date: {_get_header(headers, 'Date')}\n"
        f"Labels: {', '.join(msg.get('labelIds', []))}\n"
        f"Has Unsubscribe: {bool(_get_header(headers, 'List-Unsubscribe'))}\n\n"
        f"Body:\n{body}"
    )
