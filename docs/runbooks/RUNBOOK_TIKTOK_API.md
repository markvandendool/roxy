# TikTok API Credential Setup Runbook

**SKYBEAM Phase 7B — STORY-029**
**Last Verified:** 2026-01-10

This runbook guides you through setting up TikTok API credentials for the SKYBEAM publisher.

---

## Prerequisites

- TikTok account (personal or business)
- TikTok Developer Portal access
- Python 3.8+ with pip

## Overview

The TikTok publisher can operate in two modes:

1. **API Mode** - Direct upload via TikTok Content Posting API
2. **Handoff Mode** - Generate upload packs for manual posting (no credentials needed)

This runbook covers API Mode setup. Handoff Mode works automatically when credentials are absent.

---

## TikTok API Landscape

TikTok offers several APIs:

| API | Purpose | Access Level |
|-----|---------|--------------|
| Content Posting API | Upload videos | Requires approval |
| Login Kit | User authentication | Open |
| Share Kit | Share to TikTok | Open |

For automated publishing, you need the **Content Posting API**, which requires:
- Developer account approval
- App review process
- Business verification (for some features)

---

## Step 1: Create TikTok Developer Account

1. Go to [TikTok Developer Portal](https://developers.tiktok.com/)
2. Click **Log in** and sign in with your TikTok account
3. Accept the Developer Terms of Service
4. Complete your developer profile

## Step 2: Create an Application

1. In the Developer Portal, go to **Manage apps**
2. Click **Create app**
3. Fill in app details:
   - App name: `SKYBEAM Publisher`
   - App description: `Automated short-form video publisher`
   - App icon: (upload a 100x100 PNG)
   - Category: `Content & Publishing`
4. Click **Create**

## Step 3: Configure Products

1. In your app settings, go to **Add products**
2. Enable **Login Kit**:
   - Redirect URI: `http://localhost:8080/callback`
   - Scopes: `user.info.basic`
3. Enable **Content Posting API** (if available):
   - This requires additional approval
   - Click **Apply** and follow the review process

## Step 4: Get Client Credentials

1. Go to your app's **Overview** page
2. Note your credentials:
   - **Client Key** (also called App ID)
   - **Client Secret**
3. These are found under "Keys and Credentials"

## Step 5: Generate Access Token

Install required library:

```bash
pip install requests
```

Create token generation script (`generate_tiktok_token.py`):

```python
#!/usr/bin/env python3
"""Generate TikTok OAuth token for SKYBEAM."""

import json
import webbrowser
import http.server
import socketserver
import urllib.parse
import requests
from pathlib import Path

# Your TikTok app credentials
CLIENT_KEY = "your_client_key_here"
CLIENT_SECRET = "your_client_secret_here"
REDIRECT_URI = "http://localhost:8080/callback"

# TikTok OAuth endpoints
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this window.</p>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed")

def main():
    # Step 1: Open authorization URL
    auth_params = {
        "client_key": CLIENT_KEY,
        "redirect_uri": REDIRECT_URI,
        "scope": "user.info.basic,video.upload,video.publish",
        "response_type": "code",
        "state": "skybeam_auth"
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("Opening browser for TikTok authorization...")
    webbrowser.open(auth_url)

    # Step 2: Start local server to receive callback
    with socketserver.TCPServer(("", 8080), CallbackHandler) as httpd:
        httpd.auth_code = None
        print("Waiting for authorization callback on port 8080...")
        while httpd.auth_code is None:
            httpd.handle_request()
        auth_code = httpd.auth_code

    print(f"Received authorization code")

    # Step 3: Exchange code for tokens
    token_data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(TOKEN_URL, data=token_data)
    tokens = response.json()

    if "access_token" not in tokens:
        print(f"Error getting tokens: {tokens}")
        return 1

    # Step 4: Save credentials
    output = Path.home() / ".roxy" / "credentials" / "tiktok_oauth.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    creds_data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_in": tokens.get("expires_in", 86400),
        "token_type": tokens.get("token_type", "Bearer"),
        "scope": tokens.get("scope", ""),
        "open_id": tokens.get("open_id", "")
    }

    with open(output, "w") as f:
        json.dump(creds_data, f, indent=2)

    print(f"Credentials saved to: {output}")
    print("TikTok API setup complete!")
    return 0

if __name__ == "__main__":
    exit(main())
```

**Important:** Replace `CLIENT_KEY` and `CLIENT_SECRET` with your actual values before running.

Run the script:

```bash
python generate_tiktok_token.py
```

## Step 6: Verify Credentials

Run the SKYBEAM credential validator:

```bash
~/.roxy/bin/validate_credentials.py --tiktok
```

Expected output:
```
TikTok Credentials: PASS
  - File exists: ~/.roxy/credentials/tiktok_oauth.json
  - Has client_key: Yes
  - Has client_secret: Yes
  - Has access_token: Yes
```

**Note:** The validator accepts both `tiktok_oauth.json` (primary) and `tiktok_credentials.json` (fallback).

---

## Credential File Format

The `tiktok_oauth.json` file should contain:

```json
{
  "client_key": "awxxxx",
  "client_secret": "xxxxxxxx",
  "access_token": "act.xxxx",
  "refresh_token": "rft.xxxx",
  "expires_in": 86400,
  "token_type": "Bearer",
  "scope": "user.info.basic,video.upload",
  "open_id": "xxxx"
}
```

**Required fields:**
- `client_key` - Your TikTok app's client key
- `client_secret` - Your TikTok app's client secret

**Optional but recommended:**
- `access_token` - Current access token (expires in ~24h)
- `refresh_token` - Token to get new access tokens
- `open_id` - TikTok user's unique identifier

---

## Token Refresh

TikTok access tokens expire in 24 hours. To refresh:

```python
import requests

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

response = requests.post(TOKEN_URL, data={
    "client_key": CLIENT_KEY,
    "client_secret": CLIENT_SECRET,
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN
})

new_tokens = response.json()
# Update tiktok_credentials.json with new access_token
```

The SKYBEAM publisher handles token refresh automatically when credentials are present.

---

## Sandbox vs Production

TikTok provides two environments:

| Environment | Purpose | Limits |
|-------------|---------|--------|
| Sandbox | Testing | 20 API calls/day, content not public |
| Production | Live publishing | Full API access, requires approval |

### Sandbox Mode

- Enabled by default for new apps
- Videos are only visible to you
- Limited API quota
- Good for testing pipeline

### Production Mode

To request production access:

1. Go to your app in Developer Portal
2. Click **Submit for review**
3. Provide:
   - App demo video
   - Privacy policy URL
   - Terms of service URL
4. Wait for TikTok review (can take 1-2 weeks)

---

## Troubleshooting

### "Application not approved for Content Posting API"

The Content Posting API requires explicit approval. Options:
1. Apply for access in Developer Portal
2. Use Handoff Mode (manual uploads) until approved

### "Invalid client_key"

Verify your client_key matches exactly what's in Developer Portal. Common issues:
- Extra whitespace
- Wrong app selected
- Copied App ID instead of Client Key

### "Token expired"

Access tokens expire in 24 hours. The publisher should auto-refresh, but you can manually refresh using the script above.

### "User not authorized"

The TikTok account that authorized the app must match the account you're publishing to. Re-run the authorization flow with the correct account.

### "Rate limit exceeded"

Sandbox: 20 calls/day
Production: Higher limits based on app tier

Wait for rate limit reset or apply for higher quota.

---

## Handoff Mode (No API)

If you cannot get API access, SKYBEAM operates in Handoff Mode:

1. Publisher creates upload packs in `~/.roxy/content-pipeline/publish/exports/`
2. Each pack contains:
   - Video file (MP4)
   - Metadata (JSON)
   - Caption text
   - Thumbnail (if available)
3. Manually upload via TikTok app or web

Handoff Mode is automatic when credentials are missing.

---

## Security Notes

1. **Never commit credentials to git** - `.gitignore` should exclude `credentials/`
2. **Restrict file permissions**: `chmod 600 ~/.roxy/credentials/tiktok_credentials.json`
3. **Rotate tokens regularly** - Re-authorize every 30 days for security
4. **Use separate test account** - Don't use personal account for development

---

## Related Files

| File | Purpose |
|------|---------|
| `~/.roxy/credentials/tiktok_oauth.json` | API credentials (primary) |
| `~/.roxy/credentials/tiktok_credentials.json` | API credentials (fallback) |
| `~/.roxy/services/publish/tiktok_publisher.py` | Publisher service |
| `~/.roxy/bin/validate_credentials.py` | Credential validator |
| `~/.roxy/content-pipeline/publish/exports/` | Handoff packs |

---

*End of Runbook*
