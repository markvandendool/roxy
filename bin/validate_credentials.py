#!/usr/bin/env python3
"""
SKYBEAM Credential Validator (STORY-028/029)

Validates presence and format of platform credentials.

Usage:
    validate_credentials.py              Check all platforms
    validate_credentials.py --youtube    Check YouTube only
    validate_credentials.py --tiktok     Check TikTok only
    validate_credentials.py --json       Output as JSON

Exit codes:
    0 = All checked platforms PASS
    1 = One or more platforms FAIL
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Paths
CREDENTIALS_DIR = Path.home() / ".roxy" / "credentials"
YOUTUBE_CREDS = CREDENTIALS_DIR / "youtube_oauth.json"
# Primary: tiktok_oauth.json (matches publisher), Fallback: tiktok_credentials.json
TIKTOK_CREDS_PRIMARY = CREDENTIALS_DIR / "tiktok_oauth.json"
TIKTOK_CREDS_FALLBACK = CREDENTIALS_DIR / "tiktok_credentials.json"

# ANSI colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_json(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Load JSON file, return (success, data)."""
    try:
        with open(path, "r") as f:
            return True, json.load(f)
    except FileNotFoundError:
        return False, {"error": "File not found"}
    except json.JSONDecodeError as e:
        return False, {"error": f"Invalid JSON: {e}"}


def validate_youtube() -> Dict[str, Any]:
    """Validate YouTube OAuth credentials."""
    result = {
        "platform": "youtube",
        "file": str(YOUTUBE_CREDS),
        "status": "FAIL",
        "checks": []
    }

    # Check file exists
    if not YOUTUBE_CREDS.exists():
        result["checks"].append({
            "name": "file_exists",
            "status": "FAIL",
            "message": f"File not found: {YOUTUBE_CREDS}"
        })
        return result

    result["checks"].append({
        "name": "file_exists",
        "status": "PASS",
        "message": f"File exists: {YOUTUBE_CREDS}"
    })

    # Load and validate JSON
    success, data = load_json(YOUTUBE_CREDS)
    if not success:
        result["checks"].append({
            "name": "valid_json",
            "status": "FAIL",
            "message": data.get("error", "Unknown error")
        })
        return result

    result["checks"].append({
        "name": "valid_json",
        "status": "PASS",
        "message": "Valid JSON format"
    })

    # Check required fields
    required_fields = ["refresh_token", "client_id", "client_secret"]
    missing = [f for f in required_fields if f not in data or not data[f]]

    if missing:
        result["checks"].append({
            "name": "required_fields",
            "status": "FAIL",
            "message": f"Missing fields: {', '.join(missing)}"
        })
        return result

    result["checks"].append({
        "name": "required_fields",
        "status": "PASS",
        "message": "All required fields present"
    })

    # Check refresh_token format (should start with 1//)
    refresh_token = data.get("refresh_token", "")
    if not refresh_token.startswith("1//"):
        result["checks"].append({
            "name": "refresh_token_format",
            "status": "WARN",
            "message": "refresh_token may be in unexpected format"
        })
    else:
        result["checks"].append({
            "name": "refresh_token_format",
            "status": "PASS",
            "message": "refresh_token format valid"
        })

    # Check scopes
    scopes = data.get("scopes", [])
    has_upload_scope = any("youtube.upload" in s for s in scopes)

    if not has_upload_scope:
        result["checks"].append({
            "name": "upload_scope",
            "status": "WARN",
            "message": "youtube.upload scope not found (may still work)"
        })
    else:
        result["checks"].append({
            "name": "upload_scope",
            "status": "PASS",
            "message": "youtube.upload scope present"
        })

    # Determine overall status
    failures = [c for c in result["checks"] if c["status"] == "FAIL"]
    if failures:
        result["status"] = "FAIL"
    else:
        result["status"] = "PASS"

    return result


def validate_tiktok() -> Dict[str, Any]:
    """Validate TikTok API credentials."""
    # Check both possible file locations
    tiktok_creds = None
    if TIKTOK_CREDS_PRIMARY.exists():
        tiktok_creds = TIKTOK_CREDS_PRIMARY
    elif TIKTOK_CREDS_FALLBACK.exists():
        tiktok_creds = TIKTOK_CREDS_FALLBACK

    result = {
        "platform": "tiktok",
        "file": str(tiktok_creds) if tiktok_creds else str(TIKTOK_CREDS_PRIMARY),
        "status": "FAIL",
        "checks": []
    }

    # Check file exists
    if not tiktok_creds:
        result["checks"].append({
            "name": "file_exists",
            "status": "FAIL",
            "message": f"File not found: {TIKTOK_CREDS_PRIMARY} or {TIKTOK_CREDS_FALLBACK}"
        })
        return result

    result["checks"].append({
        "name": "file_exists",
        "status": "PASS",
        "message": f"File exists: {tiktok_creds}"
    })

    # Load and validate JSON
    success, data = load_json(tiktok_creds)
    if not success:
        result["checks"].append({
            "name": "valid_json",
            "status": "FAIL",
            "message": data.get("error", "Unknown error")
        })
        return result

    result["checks"].append({
        "name": "valid_json",
        "status": "PASS",
        "message": "Valid JSON format"
    })

    # Check required fields
    required_fields = ["client_key", "client_secret"]
    missing = [f for f in required_fields if f not in data or not data[f]]

    if missing:
        result["checks"].append({
            "name": "required_fields",
            "status": "FAIL",
            "message": f"Missing fields: {', '.join(missing)}"
        })
        return result

    result["checks"].append({
        "name": "required_fields",
        "status": "PASS",
        "message": "All required fields present"
    })

    # Check for access token (optional but useful)
    access_token = data.get("access_token", "")
    if access_token:
        # TikTok access tokens typically start with "act."
        if access_token.startswith("act."):
            result["checks"].append({
                "name": "access_token",
                "status": "PASS",
                "message": "access_token present (format valid)"
            })
        else:
            result["checks"].append({
                "name": "access_token",
                "status": "PASS",
                "message": "access_token present"
            })
    else:
        result["checks"].append({
            "name": "access_token",
            "status": "WARN",
            "message": "access_token not present (will need to authenticate)"
        })

    # Check for refresh token
    refresh_token = data.get("refresh_token", "")
    if refresh_token:
        # TikTok refresh tokens typically start with "rft."
        if refresh_token.startswith("rft."):
            result["checks"].append({
                "name": "refresh_token",
                "status": "PASS",
                "message": "refresh_token present (format valid)"
            })
        else:
            result["checks"].append({
                "name": "refresh_token",
                "status": "PASS",
                "message": "refresh_token present"
            })
    else:
        result["checks"].append({
            "name": "refresh_token",
            "status": "WARN",
            "message": "refresh_token not present (token refresh unavailable)"
        })

    # Check token expiry info
    expires_in = data.get("expires_in")
    if expires_in is not None:
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            hours = expires_in / 3600
            result["checks"].append({
                "name": "token_expiry",
                "status": "PASS",
                "message": f"expires_in: {hours:.1f} hours"
            })
        else:
            result["checks"].append({
                "name": "token_expiry",
                "status": "WARN",
                "message": "expires_in invalid or expired"
            })

    # Determine overall status
    failures = [c for c in result["checks"] if c["status"] == "FAIL"]
    if failures:
        result["status"] = "FAIL"
    else:
        result["status"] = "PASS"

    return result


def print_result(result: Dict[str, Any]) -> None:
    """Print validation result in human-readable format."""
    platform = result["platform"].upper()
    status = result["status"]

    if status == "PASS":
        status_str = f"{GREEN}PASS{RESET}"
    else:
        status_str = f"{RED}FAIL{RESET}"

    print(f"\n{BOLD}{platform} Credentials:{RESET} {status_str}")
    print(f"  File: {result['file']}")

    for check in result["checks"]:
        name = check["name"]
        check_status = check["status"]
        message = check["message"]

        if check_status == "PASS":
            icon = f"{GREEN}[OK]{RESET}"
        elif check_status == "WARN":
            icon = f"{YELLOW}[WARN]{RESET}"
        else:
            icon = f"{RED}[FAIL]{RESET}"

        print(f"  {icon} {name}: {message}")


def main():
    parser = argparse.ArgumentParser(
        description="SKYBEAM Credential Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    validate_credentials.py              Check all platforms
    validate_credentials.py --youtube    Check YouTube only
    validate_credentials.py --tiktok     Check TikTok only
    validate_credentials.py --json       Output as JSON
"""
    )
    parser.add_argument("--youtube", action="store_true", help="Check YouTube only")
    parser.add_argument("--tiktok", action="store_true", help="Check TikTok only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Determine which platforms to check
    check_youtube = args.youtube or (not args.youtube and not args.tiktok)
    check_tiktok = args.tiktok or (not args.youtube and not args.tiktok)

    results = []

    if check_youtube:
        results.append(validate_youtube())

    if check_tiktok:
        results.append(validate_tiktok())

    # Output
    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        print(f"{BOLD}SKYBEAM Credential Validator{RESET}")
        print("=" * 40)

        for result in results:
            print_result(result)

        print()
        print("=" * 40)

        # Summary
        all_pass = all(r["status"] == "PASS" for r in results)
        if all_pass:
            print(f"{GREEN}All credentials validated successfully{RESET}")
        else:
            failed = [r["platform"] for r in results if r["status"] != "PASS"]
            print(f"{RED}Failed: {', '.join(failed)}{RESET}")

    # Exit code
    all_pass = all(r["status"] == "PASS" for r in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
