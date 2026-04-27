# Gmail Triage & Scheduling Agent - Setup

## 1. Google Cloud Credentials

You need OAuth2 credentials to access the Gmail and Calendar APIs.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API** and **Google Calendar API**:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API" and click **Enable**
   - Search for "Google Calendar API" and click **Enable**
4. Create OAuth credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - If prompted, configure the OAuth consent screen first:
     - Choose **External** user type
     - Fill in the required fields (app name, support email)
     - Add scopes:
       - `https://www.googleapis.com/auth/gmail.readonly`
       - `https://www.googleapis.com/auth/gmail.compose`
       - `https://www.googleapis.com/auth/calendar.readonly`
     - Add your email as a test user
   - For Application type, choose **Desktop app**
   - Download the JSON file and save it as `credentials.json` in this directory

**Note:** If you previously authorized with only Gmail scope, delete `token.json` and re-run to authorize with both scopes.

## 2. AWS Credentials

The agent uses Amazon Bedrock. Make sure your AWS credentials are configured with access to Bedrock:

```bash
aws configure
# or use SSO:
aws sso login --profile your-profile
```

Your IAM user/role needs the `bedrock:InvokeModelWithResponseStream` permission for the Claude model.

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Agent

```bash
# Default: triage last 7 days of email
python gmail_agent.py

# Custom prompt via command line argument
python gmail_agent.py "Schedule a meeting with alice@example.com and bob@example.com to discuss the Q2 roadmap"

python gmail_agent.py "What bills do I have due this week?"
```

On first run, a browser window will open asking you to authorize Gmail and Calendar access. After authorizing, a `token.json` file is saved so you won't need to re-authorize on future runs.

## Files

- `gmail_agent.py` - Main agent script with system prompt and CLI argument handling
- `gmail_tools.py` - Strands `@tool` functions for Gmail API access
- `calendar_tools.py` - Strands `@tool` for reading Google Calendar events
- `scheduling_tools.py` - Strands `@tool` functions for When2Meet and email drafting
- `auth.py` - Shared Google OAuth2 authentication
- `credentials.json` - Your Google OAuth credentials (not committed to git)
- `token.json` - Auto-generated auth token (not committed to git)

## Notes

- The agent uses **read-only** Gmail and Calendar access - it cannot modify or delete anything
- Emails are truncated to 3000 characters to manage token usage
- The `List-Unsubscribe` header is used as a signal for marketing/bulk email
- Gmail category labels (CATEGORY_PROMOTIONS, CATEGORY_SOCIAL) help filter noise
- When2Meet events are created via their web form endpoint (no official API exists)
- The draft email tool creates a draft in your Gmail account - it does not send automatically, you review and send from Gmail
