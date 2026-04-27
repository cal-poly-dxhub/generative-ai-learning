# Gmail Triage & Scheduling Agent

An AI-powered email assistant built with [Strands Agents SDK](https://strandsagents.com/) that reviews your Gmail inbox, surfaces items needing your attention, and helps you schedule meetings with When2Meet -- all from the command line.

## What It Does

This agent combines two capabilities:

### 1. Email Triage

The agent scans your last X days of Gmail and filters out the noise. It skips marketing emails, newsletters, promotional content, and automated notifications, then presents what actually matters -- grouped by urgency:

- **Action Required** -- Bills due, unanswered requests, approaching deadlines
- **Receipts & Financial** -- Purchase confirmations, bank alerts, invoices
- **FYI - Worth Reading** -- Important context that doesn't need immediate action

The agent uses multiple signals to separate signal from noise:
- Gmail's built-in category labels (`CATEGORY_PROMOTIONS`, `CATEGORY_SOCIAL`)
- The `List-Unsubscribe` header (present on virtually all bulk/marketing email)
- Whether you're in the `To` field vs. `CC`/`BCC`
- Email content analysis for bills, receipts, and direct requests

When the agent is unsure about an email, it fetches the full message body for deeper inspection before making a judgment.

### 2. Meeting Scheduling with When2Meet

When you need to schedule a group meeting, the agent handles the entire workflow:

1. **Checks your Google Calendar** to see when you're already booked
2. **Creates a When2Meet poll** covering only dates/times when you're actually free
3. **Drafts a Gmail email** to the attendees with the When2Meet link, saved directly to your Drafts folder for review before sending

This means the When2Meet poll won't include times you can't make, saving a round of back-and-forth.

## Architecture

```
gmail_agent.py          -- Entry point, CLI arg parsing, agent configuration
    |
    |-- Agent (Strands SDK)
    |     |-- Model: Claude via Amazon Bedrock
    |     |-- System Prompt: triage + scheduling instructions
    |     |-- Tools:
    |           |-- fetch_recent_emails    (gmail_tools.py)
    |           |-- get_email_details      (gmail_tools.py)
    |           |-- get_calendar_events    (calendar_tools.py)
    |           |-- create_when2meet       (scheduling_tools.py)
    |           |-- draft_meeting_email    (scheduling_tools.py)
    |
    |-- auth.py  -- Shared Google OAuth2 (Gmail + Calendar)
```

### How It Works Under the Hood

The agent is built on [Strands Agents SDK](https://strandsagents.com/), which implements a tool-use loop:

1. The user's prompt (from CLI or default) is sent to Claude on Amazon Bedrock
2. Claude reads the system prompt and decides which tools to call
3. Strands executes the tool calls and returns results to Claude
4. Claude reasons over the results and may call additional tools (e.g., fetching full email bodies for ambiguous messages)
5. Once Claude has enough information, it generates the final response

The agent doesn't follow a hardcoded script. The system prompt provides guidelines, but Claude decides the order and combination of tool calls based on the specific request.

## Tools

### Gmail Tools (`gmail_tools.py`)

| Tool | Description |
|------|-------------|
| `fetch_recent_emails` | Fetches email metadata (subject, sender, date, labels, snippet) for the last N days. Returns up to 50 emails with enough context for the agent to triage without reading full bodies. |
| `get_email_details` | Fetches the full body of a specific email by ID. Used when the agent needs more context to determine if an email is actionable. Handles multipart MIME, base64 decoding, and HTML-to-text conversion. |

### Calendar Tools (`calendar_tools.py`)

| Tool | Description |
|------|-------------|
| `get_calendar_events` | Reads upcoming events from Google Calendar, grouped by date. The agent uses this to identify free time slots before creating a When2Meet poll. |

### Scheduling Tools (`scheduling_tools.py`)

| Tool | Description |
|------|-------------|
| `create_when2meet` | Creates a When2Meet scheduling poll by POSTing to When2Meet's form endpoint (`SaveNewEvent.php`). Returns the shareable poll URL. When2Meet has no official API -- this uses the same HTTP request the website makes. |
| `draft_meeting_email` | Creates a draft email in the user's Gmail account via the Drafts API. The email includes the When2Meet link and a message to attendees. The draft is **not sent automatically** -- the user reviews and sends from Gmail. |

### Authentication (`auth.py`)

All Google API access goes through a shared OAuth2 module. On first run, it opens a browser for authorization and caches the token in `token.json`. Subsequent runs reuse the cached token, refreshing automatically when expired.

Required OAuth scopes:
- `gmail.readonly` -- Read email metadata and bodies
- `gmail.compose` -- Create draft emails
- `calendar.readonly` -- Read calendar events

## Usage

```bash
# Default: triage the last 7 days of email
python gmail_agent.py

# Ask a specific question about your email
python gmail_agent.py "Do I have any bills due this week?"

# Schedule a meeting
python gmail_agent.py "Schedule a meeting with alice@example.com and bob@example.com to discuss the Q2 roadmap"

# Combine concerns
python gmail_agent.py "Check my email for anything urgent, and schedule a follow-up meeting with anyone who sent me something that needs discussion"
```

## Prerequisites

- **Python 3.10+**
- **AWS credentials** configured with access to Amazon Bedrock (Claude model)
- **Google Cloud project** with Gmail API and Google Calendar API enabled
- **OAuth2 Desktop App credentials** downloaded as `credentials.json`

## Setup

See [SETUP.md](SETUP.md) for detailed step-by-step instructions covering Google Cloud configuration, AWS credentials, and installation.

Quick start:

```bash
# Install dependencies
pip install -r requirements.txt

# Place your Google OAuth credentials file
cp ~/Downloads/client_secret_*.json credentials.json

# Run (first run opens browser for Google authorization)
python gmail_agent.py
```

## Project Structure

```
.
├── gmail_agent.py        # Main entry point and agent configuration
├── gmail_tools.py        # @tool functions for Gmail read access
├── calendar_tools.py     # @tool function for Google Calendar read access
├── scheduling_tools.py   # @tool functions for When2Meet and Gmail draft creation
├── auth.py               # Shared Google OAuth2 authentication
├── requirements.txt      # Python dependencies
├── SETUP.md              # Detailed setup instructions
├── README.md             # This file
└── .gitignore            # Excludes credentials, tokens, and caches
```

## Security & Privacy

- **Read-only email and calendar access** -- the agent cannot delete, modify, or send emails (only create drafts)
- **Email bodies are truncated** to 3,000 characters to limit token usage and data exposure
- **Credentials stay local** -- `credentials.json` and `token.json` are gitignored
- **No data is stored** -- email content is processed in-memory during the agent run and not persisted
- **When2Meet events are public** -- anyone with the link can view the poll (this is how When2Meet works by design)
