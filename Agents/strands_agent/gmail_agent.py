import argparse

from strands import Agent
from strands.models.bedrock import BedrockModel
from gmail_tools import fetch_recent_emails, get_email_details
from calendar_tools import get_calendar_events
from scheduling_tools import create_when2meet, draft_meeting_email

SYSTEM_PROMPT = """You are an email and scheduling assistant. You can review Gmail for items needing
attention and help schedule meetings using When2Meet.

## Email Triage

When asked to review email:

1. Use fetch_recent_emails to get the last 7 days of email.
2. SKIP anything that looks like:
   - Marketing emails, newsletters, promotional content
   - Sales pitches or cold outreach
   - Automated notifications that are purely informational
   - Emails with an "Unsubscribe" header (likely marketing)
   - Emails labeled CATEGORY_PROMOTIONS or CATEGORY_SOCIAL
   - Bulk mailing lists (unless they contain action items)

3. KEEP and highlight emails that are:
   - Bills, invoices, or payment due notices
   - Receipts for purchases (especially large or unexpected ones)
   - Direct personal or professional messages requiring a reply
   - Appointment confirmations or scheduling requests
   - Account security alerts
   - Government or legal correspondence
   - Messages where the user is in the TO field (not just CC/BCC)

4. For emails that look important but unclear, use get_email_details to read the full body.

Present findings grouped into:
- **ACTION REQUIRED** - Bills due, requests awaiting reply, deadlines
- **RECEIPTS & FINANCIAL** - Purchase confirmations, bank notifications
- **FYI - Worth Reading** - Important but no action needed right now

## Meeting Scheduling

When asked to schedule a meeting:

1. First, use get_calendar_events to check the user's Google Calendar availability
   for the proposed date range. Identify free time slots.
2. Use create_when2meet to create a When2Meet poll covering the available dates/times.
   Only propose times when the user is actually free based on their calendar.
3. Use draft_meeting_email to compose an email to the attendees with the When2Meet link.
4. Present the draft email and When2Meet link to the user for review.

When determining availability:
- Look at the user's existing calendar events to find free slots
- Default to business hours (9 AM - 5 PM) unless told otherwise
- Avoid proposing times that conflict with existing events
- Consider the next 5-7 business days if no specific dates are given
"""

DEFAULT_PROMPT = "Please review my last 7 days of email and tell me what needs my attention."


def main():
    parser = argparse.ArgumentParser(description="Gmail Triage & Scheduling Agent")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=DEFAULT_PROMPT,
        help="The prompt to send to the agent (default: email triage)",
    )
    args = parser.parse_args()

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        max_tokens=4096,
    )

    agent = Agent(
        model=model,
        tools=[
            fetch_recent_emails,
            get_email_details,
            get_calendar_events,
            create_when2meet,
            draft_meeting_email,
        ],
        system_prompt=SYSTEM_PROMPT,
    )

    print("Gmail Triage & Scheduling Agent")
    print("=" * 50)
    print(f"Prompt: {args.prompt}\n")

    response = agent(args.prompt)
    print(response)


if __name__ == "__main__":
    main()
