# YouTube OAuth Credential Setup Runbook

**SKYBEAM Phase 7B — STORY-028**
**Last Verified:** 2026-01-10

This runbook guides you through setting up YouTube API credentials for the SKYBEAM publisher.

---

## Prerequisites

- Google account with access to Google Cloud Console
- YouTube channel where you want to publish Shorts
- Python 3.8+ with pip

## Overview

The YouTube publisher requires OAuth 2.0 credentials to upload videos. This involves:

1. Creating a Google Cloud project
2. Enabling the YouTube Data API v3
3. Creating OAuth 2.0 credentials
4. Generating a refresh token
5. Storing credentials for SKYBEAM

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown (top-left, next to "Google Cloud")
3. Click **New Project**
4. Enter project name: `skybeam-youtube-publisher`
5. Click **Create**
6. Wait for project creation, then select it from the dropdown

## Step 2: Enable YouTube Data API v3

1. In your project, go to **APIs & Services > Library**
2. Search for "YouTube Data API v3"
3. Click on it, then click **Enable**
4. Wait for API to be enabled

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** (unless you have Google Workspace)
3. Click **Create**
4. Fill in required fields:
   - App name: `SKYBEAM Publisher`
   - User support email: (your email)
   - Developer contact: (your email)
5. Click **Save and Continue**
6. On Scopes page, click **Add or Remove Scopes**
7. Find and select:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube`
8. Click **Update**, then **Save and Continue**
9. On Test Users page, click **Add Users**
10. Add your Google account email
11. Click **Save and Continue**, then **Back to Dashboard**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Name: `skybeam-desktop`
5. Click **Create**
6. Click **Download JSON** on the popup
7. Save the file as `client_secret.json`

## Step 5: Generate Refresh Token

Install the required library:

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Create a token generation script (`generate_youtube_token.py`):

```python
#!/usr/bin/env python3
"""Generate YouTube OAuth token for SKYBEAM."""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def main():
    # Path to your downloaded client_secret.json
    client_secret = Path("client_secret.json")
    if not client_secret.exists():
        print("ERROR: client_secret.json not found")
        print("Download it from Google Cloud Console > Credentials")
        return 1

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret),
        scopes=SCOPES
    )
    credentials = flow.run_local_server(port=8080)

    # Save credentials
    output = Path.home() / ".roxy" / "credentials" / "youtube_oauth.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    creds_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes)
    }

    with open(output, "w") as f:
        json.dump(creds_data, f, indent=2)

    print(f"Credentials saved to: {output}")
    print("YouTube OAuth setup complete!")
    return 0

if __name__ == "__main__":
    exit(main())
```

Run the script:

```bash
python generate_youtube_token.py
```

A browser window will open. Sign in with your Google account and authorize the app.

## Step 6: Verify Credentials

Run the SKYBEAM credential validator:

```bash
~/.roxy/bin/validate_credentials.py --youtube
```

Expected output:
```
YouTube OAuth: PASS
  - File exists: ~/.roxy/credentials/youtube_oauth.json
  - Has refresh_token: Yes
  - Has client_id: Yes
  - Scopes include youtube.upload: Yes
```

---

## Credential File Format

The `youtube_oauth.json` file should contain:

```json
{
  "token": "ya29.xxx...",
  "refresh_token": "1//xxx...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "xxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxx",
  "scopes": [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
  ]
}
```

**Required fields:**
- `refresh_token` - Long-lived token for offline access
- `client_id` - OAuth client ID
- `client_secret` - OAuth client secret
- `scopes` - Must include `youtube.upload`

---

## Troubleshooting

### "Access blocked: This app's request is invalid"

The OAuth consent screen is not properly configured. Ensure:
1. You added yourself as a test user
2. The app is in "Testing" status
3. You're signing in with the test user account

### "Token has been expired or revoked"

Re-run the token generation script to get a fresh refresh token.

### "Quota exceeded"

YouTube API has daily quotas. Check your quota usage at:
**APIs & Services > YouTube Data API v3 > Quotas**

Default quota is 10,000 units/day. Each upload costs ~1,600 units.

### "The request cannot be completed because you have exceeded your quota"

Wait 24 hours for quota reset, or request a quota increase from Google.

---

## Security Notes

1. **Never commit credentials to git** - The `.gitignore` should exclude `credentials/`
2. **Restrict file permissions**: `chmod 600 ~/.roxy/credentials/youtube_oauth.json`
3. **Rotate credentials periodically** - Re-run token generation every 6 months
4. **Use a dedicated Google account** for production publishing

---

## Switching to Production Mode

When ready for production:

1. Go to **OAuth consent screen**
2. Click **Publish App**
3. Complete Google's verification process (may take weeks)
4. Once verified, remove test user restrictions

For Shorts publishing to personal channels, "Testing" mode is usually sufficient.

---

## Related Files

| File | Purpose |
|------|---------|
| `~/.roxy/credentials/youtube_oauth.json` | OAuth credentials |
| `~/.roxy/services/publish/youtube_publisher.py` | Publisher service |
| `~/.roxy/bin/validate_credentials.py` | Credential validator |

---

*End of Runbook*
