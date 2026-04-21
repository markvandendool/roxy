#!/usr/bin/env python3
"""
MCP Server for Unified Email Access.

Provides IMAP read/search + SMTP send across multiple email accounts.
Designed for the MindSong Citadel infrastructure on Roxy.

Accounts: Gmail, Hotmail/Outlook, custom domains (Novaxe, personal, McGill)
Pattern: FastMCP + lifespan for persistent IMAP connections
Transport: stdio (local Roxy execution)

Author: MindSong Citadel / Luno Orchestrator
"""

import json
import os
import sys
import asyncio
import email as email_lib
import email.utils
import email.header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Sequence

import aiosmtplib
from imapclient import IMAPClient
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP, Context

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_PATH = os.environ.get(
    "EMAIL_MCP_CONFIG",
    str(Path(__file__).parent / "accounts.json"),
)
DEFAULT_FETCH_LIMIT = 20
MAX_FETCH_LIMIT = 100
MAX_BODY_LENGTH = 50_000  # truncate huge emails

# ---------------------------------------------------------------------------
# Account Configuration
# ---------------------------------------------------------------------------

class AccountConfig(BaseModel):
    """Single email account configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., description="Human label, e.g. 'gmail', 'hotmail', 'novaxe'")
    email: str = Field(..., description="Full email address")
    imap_host: str = Field(..., description="IMAP server hostname")
    imap_port: int = Field(default=993, description="IMAP port (993 for SSL)")
    smtp_host: str = Field(..., description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP port (587 for STARTTLS)")
    username: str = Field(..., description="Login username (usually same as email)")
    password: str = Field(..., description="App-specific password")
    use_ssl: bool = Field(default=True, description="Use SSL for IMAP")
    use_starttls: bool = Field(default=True, description="Use STARTTLS for SMTP")
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates (set False for self-signed/mismatched certs)")


def load_accounts() -> Dict[str, AccountConfig]:
    """Load account configs from JSON file."""
    path = Path(CONFIG_PATH)
    if not path.exists():
        print(f"WARNING: Config not found at {CONFIG_PATH}, using empty accounts", file=sys.stderr)
        return {}
    with open(path) as f:
        raw = json.load(f)
    accounts: Dict[str, AccountConfig] = {}
    for entry in raw.get("accounts", []):
        cfg = AccountConfig(**entry)
        accounts[cfg.name] = cfg
    return accounts


# ---------------------------------------------------------------------------
# IMAP Connection Pool (lifespan-managed)
# ---------------------------------------------------------------------------

class IMAPPool:
    """Manages persistent IMAP connections per account."""

    def __init__(self, accounts: Dict[str, AccountConfig]):
        self._accounts = accounts
        self._connections: Dict[str, IMAPClient] = {}

    def _connect(self, name: str) -> IMAPClient:
        cfg = self._accounts[name]
        ssl_context = None
        if cfg.use_ssl and not cfg.ssl_verify:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        client = IMAPClient(
            cfg.imap_host,
            port=cfg.imap_port,
            ssl=cfg.use_ssl,
            ssl_context=ssl_context,
        )
        client.login(cfg.username, cfg.password)
        return client

    def get(self, name: str) -> IMAPClient:
        """Get or create an IMAP connection for the named account."""
        if name not in self._accounts:
            raise ValueError(f"Unknown account '{name}'. Available: {list(self._accounts.keys())}")
        conn = self._connections.get(name)
        if conn is not None:
            try:
                conn.noop()  # keep-alive check
                return conn
            except Exception:
                pass  # reconnect below
        conn = self._connect(name)
        self._connections[name] = conn
        return conn

    def close_all(self):
        for name, conn in self._connections.items():
            try:
                conn.logout()
            except Exception:
                pass
        self._connections.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decode_header_value(raw: str) -> str:
    """Decode RFC 2047 encoded header values."""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def extract_body(msg: email_lib.message.Message, max_len: int = MAX_BODY_LENGTH) -> str:
    """Extract plain-text body from a parsed email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
        if not body:
            # fallback: try html
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = f"[HTML content]\n{payload.decode(charset, errors='replace')}"
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body[:max_len]


def parse_envelope(uid: int, data: dict) -> Dict[str, Any]:
    """Parse IMAP ENVELOPE + FLAGS into a clean dict."""
    envelope = data.get(b"ENVELOPE") or data.get("ENVELOPE")
    flags = data.get(b"FLAGS") or data.get("FLAGS") or ()
    size = data.get(b"RFC822.SIZE") or data.get("RFC822.SIZE") or 0

    if envelope is None:
        return {"uid": uid, "error": "No envelope data"}

    def addr_str(addrs):
        if not addrs:
            return ""
        results = []
        for a in addrs:
            name = a.name.decode(errors="replace") if a.name else ""
            mailbox = a.mailbox.decode(errors="replace") if a.mailbox else ""
            host = a.host.decode(errors="replace") if a.host else ""
            addr = f"{mailbox}@{host}" if host else mailbox
            results.append(f"{name} <{addr}>" if name else addr)
        return ", ".join(results)

    subject_raw = envelope.subject
    if isinstance(subject_raw, bytes):
        subject_raw = subject_raw.decode(errors="replace")
    subject = decode_header_value(subject_raw) if subject_raw else "(no subject)"

    date = envelope.date
    if isinstance(date, datetime):
        date_str = date.isoformat()
    elif date:
        date_str = str(date)
    else:
        date_str = ""

    flag_strs = []
    for f in flags:
        flag_strs.append(f.decode(errors="replace") if isinstance(f, bytes) else str(f))

    return {
        "uid": uid,
        "subject": subject,
        "from": addr_str(envelope.from_),
        "to": addr_str(envelope.to),
        "cc": addr_str(envelope.cc),
        "date": date_str,
        "message_id": (envelope.message_id.decode(errors="replace")
                       if envelope.message_id else ""),
        "in_reply_to": (envelope.in_reply_to.decode(errors="replace")
                        if envelope.in_reply_to else ""),
        "flags": flag_strs,
        "size": size,
    }


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def app_lifespan(app):
    accounts = load_accounts()
    pool = IMAPPool(accounts)
    yield {"accounts": accounts, "pool": pool}
    pool.close_all()


# ---------------------------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("email_mcp", lifespan=app_lifespan)


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class ListAccountsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'"
    )


class ListMailboxesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    account: str = Field(..., description="Account name (e.g. 'gmail', 'hotmail', 'novaxe', 'personal', 'mcgill')")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SearchEmailsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: Optional[str] = Field(
        default=None,
        description="Account name to search. Omit to search ALL accounts."
    )
    mailbox: str = Field(
        default="INBOX",
        description="Mailbox/folder to search (e.g. 'INBOX', 'Sent', '[Gmail]/All Mail')"
    )
    query: Optional[str] = Field(
        default=None,
        description="IMAP search criteria. Examples: 'FROM \"alice@example.com\"', 'SUBJECT \"invoice\"', 'SINCE 01-Apr-2026', 'UNSEEN', 'TEXT \"meeting\"'. Combine with spaces for AND."
    )
    limit: int = Field(
        default=DEFAULT_FETCH_LIMIT,
        description="Max messages to return",
        ge=1,
        le=MAX_FETCH_LIMIT,
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        return v


class FetchMessageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: str = Field(..., description="Account name")
    uid: int = Field(..., description="Message UID from search results")
    mailbox: str = Field(default="INBOX", description="Mailbox containing the message")
    include_body: bool = Field(default=True, description="Include full message body")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class FetchThreadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: str = Field(..., description="Account name")
    message_id: str = Field(..., description="Message-ID header of any message in the thread")
    mailbox: str = Field(default="[Gmail]/All Mail", description="Mailbox to search thread in")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SendEmailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: str = Field(..., description="Account to send FROM")
    to: List[str] = Field(..., description="Recipient email addresses", min_length=1)
    subject: str = Field(..., description="Email subject line", min_length=1, max_length=500)
    body: str = Field(..., description="Plain-text email body")
    html_body: Optional[str] = Field(default=None, description="Optional HTML body")
    cc: Optional[List[str]] = Field(default=None, description="CC recipients")
    bcc: Optional[List[str]] = Field(default=None, description="BCC recipients")
    reply_to_message_id: Optional[str] = Field(
        default=None,
        description="Message-ID to reply to (sets In-Reply-To and References headers)"
    )


class MarkEmailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: str = Field(..., description="Account name")
    uids: List[int] = Field(..., description="Message UIDs to modify", min_length=1)
    mailbox: str = Field(default="INBOX")
    action: str = Field(
        ...,
        description="Action: 'read', 'unread', 'star', 'unstar', 'archive', 'trash'"
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"read", "unread", "star", "unstar", "archive", "trash"}
        if v not in allowed:
            raise ValueError(f"Invalid action '{v}'. Allowed: {allowed}")
        return v


class MoveEmailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    account: str = Field(..., description="Account name")
    uids: List[int] = Field(..., description="Message UIDs to move", min_length=1)
    source_mailbox: str = Field(default="INBOX", description="Source mailbox")
    destination_mailbox: str = Field(..., description="Destination mailbox/folder")


# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

@mcp.tool(
    name="email_list_accounts",
    annotations={
        "title": "List Email Accounts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def email_list_accounts(params: ListAccountsInput, ctx: Context) -> str:
    """List all configured email accounts and their status.

    Returns account names, email addresses, and IMAP/SMTP server info
    for all accounts configured in the email MCP server.

    Args:
        params: ListAccountsInput with optional response_format

    Returns:
        str: Account list in requested format (markdown or JSON)
    """
    accounts: Dict[str, AccountConfig] = ctx.request_context.lifespan_context["accounts"]

    if not accounts:
        return "No email accounts configured. Add accounts to accounts.json."

    if params.response_format == ResponseFormat.JSON:
        data = []
        for name, cfg in accounts.items():
            data.append({
                "name": name,
                "email": cfg.email,
                "imap_host": cfg.imap_host,
                "smtp_host": cfg.smtp_host,
            })
        return json.dumps({"accounts": data, "count": len(data)}, indent=2)

    lines = ["# Email Accounts", ""]
    for name, cfg in accounts.items():
        lines.append(f"- **{name}**: {cfg.email} (IMAP: {cfg.imap_host}, SMTP: {cfg.smtp_host})")
    lines.append(f"\n_{len(accounts)} accounts configured_")
    return "\n".join(lines)


@mcp.tool(
    name="email_list_mailboxes",
    annotations={
        "title": "List Mailboxes/Folders",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def email_list_mailboxes(params: ListMailboxesInput, ctx: Context) -> str:
    """List all mailboxes (folders) for a specific email account.

    Args:
        params: ListMailboxesInput with account name

    Returns:
        str: List of mailbox names and their flags
    """
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]
    try:
        conn = pool.get(params.account)
        mailboxes = conn.list_folders()

        if params.response_format == ResponseFormat.JSON:
            data = []
            for flags, delimiter, name in mailboxes:
                flag_strs = [f.decode(errors="replace") if isinstance(f, bytes) else str(f) for f in flags]
                data.append({"name": name, "flags": flag_strs})
            return json.dumps({"account": params.account, "mailboxes": data, "count": len(data)}, indent=2)

        lines = [f"# Mailboxes for {params.account}", ""]
        for flags, delimiter, name in mailboxes:
            flag_strs = [f.decode(errors="replace") if isinstance(f, bytes) else str(f) for f in flags]
            flag_display = ", ".join(flag_strs) if flag_strs else ""
            lines.append(f"- `{name}` {f'({flag_display})' if flag_display else ''}")
        return "\n".join(lines)

    except Exception as e:
        return f"Error listing mailboxes for '{params.account}': {e}"


@mcp.tool(
    name="email_search",
    annotations={
        "title": "Search Emails",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def email_search(params: SearchEmailsInput, ctx: Context) -> str:
    """Search emails across one or all accounts using IMAP search criteria.

    Supports searching by sender, subject, date, body text, read/unread status,
    and more using standard IMAP search syntax.

    Args:
        params: SearchEmailsInput with optional account, mailbox, query, limit

    Returns:
        str: Matching messages with subject, from, date, flags

    Examples:
        - All unread: query='UNSEEN'
        - From someone: query='FROM "alice@example.com"'
        - Subject search: query='SUBJECT "invoice"'
        - Date range: query='SINCE 01-Apr-2026'
        - Combined: query='UNSEEN FROM "bob@example.com" SINCE 01-Mar-2026'
        - All recent (no query): returns latest messages
    """
    accounts: Dict[str, AccountConfig] = ctx.request_context.lifespan_context["accounts"]
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]

    target_accounts = [params.account] if params.account else list(accounts.keys())
    all_results: List[Dict[str, Any]] = []

    for acct_name in target_accounts:
        try:
            conn = pool.get(acct_name)
            conn.select_folder(params.mailbox, readonly=True)

            criteria = params.query if params.query else "ALL"
            uids = conn.search(criteria)

            # Get most recent first
            uids = sorted(uids, reverse=True)[:params.limit]

            if uids:
                fetch_data = conn.fetch(uids, ["ENVELOPE", "FLAGS", "RFC822.SIZE"])
                for uid in uids:
                    if uid in fetch_data:
                        envelope = parse_envelope(uid, fetch_data[uid])
                        envelope["account"] = acct_name
                        all_results.append(envelope)
        except Exception as e:
            all_results.append({
                "account": acct_name,
                "error": str(e),
            })

    # Trim to overall limit
    all_results = all_results[:params.limit]

    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "results": all_results,
            "count": len(all_results),
            "query": params.query,
            "mailbox": params.mailbox,
        }, indent=2, default=str)

    if not all_results:
        return f"No messages found for query: {params.query or 'ALL'}"

    lines = [f"# Email Search Results", f"Query: `{params.query or 'ALL'}` | Mailbox: `{params.mailbox}`", ""]
    for msg in all_results:
        if "error" in msg and "uid" not in msg:
            lines.append(f"- [{msg['account']}] Error: {msg['error']}")
            continue
        read_marker = "" if "\\Seen" in msg.get("flags", []) else " **[UNREAD]**"
        lines.append(f"### [{msg['account']}] {msg['subject']}{read_marker}")
        lines.append(f"- **From:** {msg['from']}")
        lines.append(f"- **Date:** {msg['date']}")
        lines.append(f"- **UID:** {msg['uid']} | **Size:** {msg.get('size', 0):,} bytes")
        if msg.get("to"):
            lines.append(f"- **To:** {msg['to']}")
        lines.append("")
    lines.append(f"_{len(all_results)} messages_")
    return "\n".join(lines)


@mcp.tool(
    name="email_fetch_message",
    annotations={
        "title": "Fetch Full Email Message",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def email_fetch_message(params: FetchMessageInput, ctx: Context) -> str:
    """Fetch full content of a specific email by UID.

    Args:
        params: FetchMessageInput with account, uid, mailbox

    Returns:
        str: Full message headers and body
    """
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]
    try:
        conn = pool.get(params.account)
        conn.select_folder(params.mailbox, readonly=True)

        fetch_keys = ["ENVELOPE", "FLAGS", "RFC822.SIZE"]
        if params.include_body:
            fetch_keys.append("RFC822")

        data = conn.fetch([params.uid], fetch_keys)
        if params.uid not in data:
            return f"Error: Message UID {params.uid} not found in {params.mailbox}"

        msg_data = data[params.uid]
        envelope = parse_envelope(params.uid, msg_data)
        envelope["account"] = params.account

        body = ""
        attachments = []
        if params.include_body:
            raw = msg_data.get(b"RFC822") or msg_data.get("RFC822")
            if raw:
                parsed = email_lib.message_from_bytes(raw)
                body = extract_body(parsed)
                # List attachments
                if parsed.is_multipart():
                    for part in parsed.walk():
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                "filename": decode_header_value(filename),
                                "content_type": part.get_content_type(),
                                "size": len(part.get_payload(decode=True) or b""),
                            })

        if params.response_format == ResponseFormat.JSON:
            envelope["body"] = body
            envelope["attachments"] = attachments
            return json.dumps(envelope, indent=2, default=str)

        lines = [
            f"# {envelope['subject']}",
            "",
            f"**From:** {envelope['from']}",
            f"**To:** {envelope['to']}",
        ]
        if envelope.get("cc"):
            lines.append(f"**CC:** {envelope['cc']}")
        lines.extend([
            f"**Date:** {envelope['date']}",
            f"**Account:** {params.account} | **UID:** {params.uid}",
            f"**Message-ID:** `{envelope.get('message_id', '')}`",
        ])
        if attachments:
            lines.append(f"\n**Attachments ({len(attachments)}):**")
            for att in attachments:
                lines.append(f"- {att['filename']} ({att['content_type']}, {att['size']:,} bytes)")
        if body:
            lines.extend(["", "---", "", body])
        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching message: {e}"


@mcp.tool(
    name="email_fetch_thread",
    annotations={
        "title": "Fetch Email Thread",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def email_fetch_thread(params: FetchThreadInput, ctx: Context) -> str:
    """Fetch all messages in a conversation thread by Message-ID.

    Uses References and In-Reply-To headers to reconstruct the thread.

    Args:
        params: FetchThreadInput with account, message_id, mailbox

    Returns:
        str: All messages in the thread, ordered chronologically
    """
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]
    try:
        conn = pool.get(params.account)
        conn.select_folder(params.mailbox, readonly=True)

        # Search by References header and Message-ID
        clean_id = params.message_id.strip("<>")
        criteria = f'OR HEADER "References" "{clean_id}" HEADER "Message-ID" "{clean_id}"'
        uids = conn.search(criteria)

        if not uids:
            # Fallback: search by In-Reply-To
            criteria = f'OR HEADER "In-Reply-To" "{clean_id}" HEADER "Message-ID" "{clean_id}"'
            uids = conn.search(criteria)

        if not uids:
            return f"No thread found for Message-ID: {params.message_id}"

        uids = sorted(uids)  # chronological order
        fetch_data = conn.fetch(uids, ["ENVELOPE", "FLAGS", "RFC822"])

        messages = []
        for uid in uids:
            if uid in fetch_data:
                msg_data = fetch_data[uid]
                envelope = parse_envelope(uid, msg_data)
                raw = msg_data.get(b"RFC822") or msg_data.get("RFC822")
                body = ""
                if raw:
                    parsed = email_lib.message_from_bytes(raw)
                    body = extract_body(parsed, max_len=10_000)
                envelope["body"] = body
                messages.append(envelope)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "thread_id": params.message_id,
                "messages": messages,
                "count": len(messages),
            }, indent=2, default=str)

        lines = [f"# Email Thread ({len(messages)} messages)", ""]
        for i, msg in enumerate(messages, 1):
            lines.append(f"## [{i}] {msg['subject']}")
            lines.append(f"**From:** {msg['from']} | **Date:** {msg['date']}")
            if msg.get("body"):
                lines.extend(["", msg["body"][:5000], ""])
            lines.append("---")
        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching thread: {e}"


@mcp.tool(
    name="email_send",
    annotations={
        "title": "Send Email",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def email_send(params: SendEmailInput, ctx: Context) -> str:
    """Send an email from a specified account via SMTP.

    Supports plain text, HTML, CC, BCC, and reply threading.

    Args:
        params: SendEmailInput with account, to, subject, body

    Returns:
        str: Confirmation with message details or error
    """
    accounts: Dict[str, AccountConfig] = ctx.request_context.lifespan_context["accounts"]

    if params.account not in accounts:
        return f"Error: Unknown account '{params.account}'. Available: {list(accounts.keys())}"

    cfg = accounts[params.account]

    try:
        # Build message
        if params.html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(params.body, "plain", "utf-8"))
            msg.attach(MIMEText(params.html_body, "html", "utf-8"))
        else:
            msg = MIMEText(params.body, "plain", "utf-8")

        msg["From"] = cfg.email
        msg["To"] = ", ".join(params.to)
        msg["Subject"] = params.subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain=cfg.email.split("@")[1])

        if params.cc:
            msg["Cc"] = ", ".join(params.cc)
        if params.reply_to_message_id:
            msg["In-Reply-To"] = params.reply_to_message_id
            msg["References"] = params.reply_to_message_id

        all_recipients = list(params.to)
        if params.cc:
            all_recipients.extend(params.cc)
        if params.bcc:
            all_recipients.extend(params.bcc)

        # Send via SMTP
        await aiosmtplib.send(
            msg,
            hostname=cfg.smtp_host,
            port=cfg.smtp_port,
            start_tls=cfg.use_starttls,
            username=cfg.username,
            password=cfg.password,
            recipients=all_recipients,
        )

        return (
            f"Email sent successfully!\n"
            f"- **From:** {cfg.email}\n"
            f"- **To:** {', '.join(params.to)}\n"
            f"- **Subject:** {params.subject}\n"
            f"- **Message-ID:** {msg['Message-ID']}"
        )

    except Exception as e:
        return f"Error sending email: {e}"


@mcp.tool(
    name="email_mark",
    annotations={
        "title": "Mark/Flag Emails",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def email_mark(params: MarkEmailInput, ctx: Context) -> str:
    """Mark emails as read/unread, star/unstar, archive, or trash.

    Args:
        params: MarkEmailInput with account, uids, action

    Returns:
        str: Confirmation of action applied
    """
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]
    try:
        conn = pool.get(params.account)
        conn.select_folder(params.mailbox)

        action_map = {
            "read": (conn.add_flags, [b"\\Seen"]),
            "unread": (conn.remove_flags, [b"\\Seen"]),
            "star": (conn.add_flags, [b"\\Flagged"]),
            "unstar": (conn.remove_flags, [b"\\Flagged"]),
            "trash": (conn.add_flags, [b"\\Deleted"]),
        }

        if params.action == "archive":
            # Gmail-specific: move to All Mail by removing INBOX label
            conn.move(params.uids, "[Gmail]/All Mail")
            return f"Archived {len(params.uids)} message(s) in {params.account}"

        if params.action in action_map:
            func, flags = action_map[params.action]
            func(params.uids, flags)
            if params.action == "trash":
                conn.expunge()
            return f"Applied '{params.action}' to {len(params.uids)} message(s) in {params.account}"

        return f"Error: Unknown action '{params.action}'"

    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="email_move",
    annotations={
        "title": "Move Emails Between Folders",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def email_move(params: MoveEmailInput, ctx: Context) -> str:
    """Move emails from one mailbox/folder to another.

    Args:
        params: MoveEmailInput with account, uids, source, destination

    Returns:
        str: Confirmation of move
    """
    pool: IMAPPool = ctx.request_context.lifespan_context["pool"]
    try:
        conn = pool.get(params.account)
        conn.select_folder(params.source_mailbox)
        conn.move(params.uids, params.destination_mailbox)
        return (
            f"Moved {len(params.uids)} message(s) from "
            f"`{params.source_mailbox}` to `{params.destination_mailbox}` "
            f"in {params.account}"
        )
    except Exception as e:
        return f"Error moving messages: {e}"


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
