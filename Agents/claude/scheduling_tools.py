import re
from typing import Optional

import requests

from strands import tool


@tool
def create_when2meet(
    event_name: str,
    dates: list[str],
    no_earlier_than: int = 9,
    no_later_than: int = 17,
    timezone: str = "America/Los_Angeles",
) -> str:
    """Create a When2Meet scheduling poll and return the shareable link.

    Use this after checking the user's calendar availability. Provide dates
    when the user has free time so attendees can vote on the best slot.

    Args:
        event_name: Name for the When2Meet event (e.g. "Team Sync")
        dates: List of dates in YYYY-MM-DD format (e.g. ["2026-04-27", "2026-04-28"])
        no_earlier_than: Earliest hour in 24h format, 0-23 (default 9 = 9 AM)
        no_later_than: Latest hour in 24h format, 0-23 (default 17 = 5 PM)
        timezone: IANA timezone string (default "America/Los_Angeles")
    """
    if not dates:
        return "Error: You must provide at least one date."

    if not event_name or event_name == "New Event Name":
        return "Error: Please provide a meaningful event name."

    resp = requests.post(
        "https://www.when2meet.com/SaveNewEvent.php",
        data={
            "NewEventName": event_name,
            "DateTypes": "SpecificDates",
            "PossibleDates": "|".join(dates),
            "NoEarlierThan": str(no_earlier_than),
            "NoLaterThan": str(no_later_than),
            "TimeZone": timezone,
        },
    )

    match = re.search(r"window\.location='([^']+)'", resp.text)
    if match:
        path = match.group(1).lstrip("./")
        url = f"https://www.when2meet.com/{path}"
        return (
            f"When2Meet event created successfully!\n"
            f"Event: {event_name}\n"
            f"Dates: {', '.join(dates)}\n"
            f"Time range: {no_earlier_than}:00 - {no_later_than}:00 ({timezone})\n"
            f"Link: {url}"
        )

    return f"Error: Failed to create When2Meet event. Response: {resp.text[:500]}"


@tool
def draft_meeting_email(
    recipients: list[str],
    subject: str,
    meeting_purpose: str,
    when2meet_link: str,
    proposed_dates: str,
    sender_name: str = "there",
) -> str:
    """Draft an email inviting recipients to fill out a When2Meet poll.

    Use this after creating a When2Meet link. Returns the draft email text
    for the user to review before sending.

    Args:
        recipients: List of email addresses to invite
        subject: Email subject line
        meeting_purpose: Brief description of what the meeting is about
        when2meet_link: The When2Meet URL to include in the email
        proposed_dates: Human-readable description of the proposed dates/times
        sender_name: Name to use in the greeting (default "there")
    """
    recipient_list = ", ".join(recipients)

    email_body = f"""To: {recipient_list}
Subject: {subject}

Hi {sender_name if sender_name != "there" else "all"},

I'd like to schedule a meeting to {meeting_purpose}.

I've created a When2Meet poll to find a time that works for everyone. The proposed dates are {proposed_dates}.

Please fill out your availability here:
{when2meet_link}

Once everyone has responded, I'll send out a calendar invite for the best time.

Thanks!
"""

    return (
        f"Draft email prepared:\n"
        f"{'=' * 50}\n"
        f"{email_body}\n"
        f"{'=' * 50}\n\n"
        f"Recipients: {recipient_list}\n"
        f"When2Meet Link: {when2meet_link}\n\n"
        f"Review the draft above. You can copy and send it from your email client."
    )
