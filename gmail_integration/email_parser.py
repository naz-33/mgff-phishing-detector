"""Gmail message MIME parsing and text extraction for ZanderEtAlFishing."""

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import email.utils
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


@dataclass
class ParsedEmail:
    """Structured representation of a parsed Gmail message."""

    message_id: str
    thread_id: str
    sender: str
    subject: str
    received_at: str  # ISO 8601 UTC
    internal_date_ms: int
    body: str
    combined_text: str
    content_type_used: str  # 'text/plain' or 'text/html' or 'empty'
    # Email authentication header signals (Track B)
    spf_pass: Optional[bool] = None
    dkim_pass: Optional[bool] = None
    dmarc_pass: Optional[bool] = None


def decode_base64url(encoded_str: str) -> str:
    """Decode a Base64URL-encoded string safely handling padding.
    
    Gmail API represents body.data in standard URL-safe Base64 without trailing '=' padding.
    """
    if not encoded_str:
        return ""
    # Add necessary '=' padding for base64 decoding
    rem = len(encoded_str) % 4
    if rem > 0:
        encoded_str += "=" * (4 - rem)
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_str.encode("utf-8"))
        # Attempt UTF-8, then fallback to latin-1
        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return decoded_bytes.decode("latin-1", errors="replace")
    except Exception:
        return ""


def html_to_plain_text(html_content: str) -> str:
    """Extract readable text from HTML content, stripping scripts and styles."""
    if not html_content or not html_content.strip():
        return ""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, and noscript elements
    for element in soup(["script", "style", "noscript", "head", "title", "meta"]):
        element.decompose()

    # Add spaces around line breaks and block elements to preserve word separation
    for br in soup.find_all("br"):
        br.replace_with("\n")

    text = soup.get_text(separator=" ")
    # Clean up redundant spaces while preserving line structure
    lines = [" ".join(line.split()) for line in text.splitlines()]
    clean_text = "\n".join(line for line in lines if line)
    return clean_text


def is_attachment_part(part: Dict[str, Any]) -> bool:
    """Determine whether a MIME part is an attachment that should be excluded from body text."""
    filename = part.get("filename")
    if filename:
        return True

    headers = part.get("headers", [])
    for h in headers:
        name = h.get("name", "").lower()
        val = h.get("value", "").lower()
        if name == "content-disposition" and "attachment" in val:
            return True
    return False


def extract_body_parts(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Recursively extract plain text and HTML body parts from a Gmail payload.
    
    Returns:
        (plain_text, html_text)
    """
    mime_type = payload.get("mimeType", "").lower()
    body_dict = payload.get("body", {})
    body_data = body_dict.get("data", "")

    # Check for direct body if not attachment
    plain_body: Optional[str] = None
    html_body: Optional[str] = None

    if not is_attachment_part(payload):
        if mime_type == "text/plain" and body_data:
            plain_body = decode_base64url(body_data)
        elif mime_type == "text/html" and body_data:
            html_body = decode_base64url(body_data)

    # If payload contains nested parts, traverse them
    parts = payload.get("parts", [])
    for part in parts:
        if is_attachment_part(part):
            continue

        p_mime = part.get("mimeType", "").lower()
        p_body_data = part.get("body", {}).get("data", "")

        if p_mime == "text/plain" and p_body_data and not plain_body:
            plain_body = decode_base64url(p_body_data)
        elif p_mime == "text/html" and p_body_data and not html_body:
            html_body = decode_base64url(p_body_data)
        elif "parts" in part:
            sub_plain, sub_html = extract_body_parts(part)
            if sub_plain and not plain_body:
                plain_body = sub_plain
            if sub_html and not html_body:
                html_body = sub_html

    return plain_body, html_body


def combine_subject_and_body(subject: str, body: str) -> str:
    """Combine email subject and body into a single string for ML inference.
    
    Maintains subject context followed by email body.
    """
    subject = (subject or "").strip()
    body = (body or "").strip()

    if subject and body:
        return f"{subject}\n\n{body}"
    elif subject:
        return subject
    elif body:
        return body
    else:
        return "Empty email content"


def parse_gmail_timestamp(date_header: Optional[str], internal_date_ms: Optional[int]) -> str:
    """Parse email timestamp into ISO 8601 UTC string.
    
    Prefers internalDate (canonical Gmail server timestamp in ms),
    falls back to RFC 2822 Date header.
    """
    if internal_date_ms:
        try:
            dt = datetime.fromtimestamp(internal_date_ms / 1000.0, tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass

    if date_header:
        try:
            parsed_tuple = email.utils.parsedate_to_datetime(date_header)
            return parsed_tuple.astimezone(timezone.utc).isoformat()
        except Exception:
            pass

    return datetime.now(timezone.utc).isoformat()


def parse_gmail_message(message_dict: Dict[str, Any]) -> ParsedEmail:
    """Parse a complete Gmail API message object into ParsedEmail.
    
    Extracts headers (Subject, From, Date), decodes body prioritizing text/plain,
    falls back to HTML-to-text, and produces combined text for ML inference.
    """
    msg_id = message_dict.get("id", "")
    thread_id = message_dict.get("threadId", "")
    internal_date_str = message_dict.get("internalDate", "0")
    try:
        internal_date_ms = int(internal_date_str)
    except (ValueError, TypeError):
        internal_date_ms = 0

    payload = message_dict.get("payload", {})
    headers = payload.get("headers", [])

    header_map = {}
    for h in headers:
        header_map[h.get("name", "").lower()] = h.get("value", "")

    subject = header_map.get("subject", "")
    sender = header_map.get("from", "")
    date_header = header_map.get("date", "")

    received_at = parse_gmail_timestamp(date_header, internal_date_ms)

    # Extract SPF / DKIM / DMARC pass signals from Authentication-Results header (Track B).
    # These are display-only trust signals; they do not affect ML inference.
    auth_header_val = header_map.get("authentication-results")
    if auth_header_val:
        auth_results_raw = auth_header_val.lower()
        spf_pass = "spf=pass" in auth_results_raw
        dkim_pass = "dkim=pass" in auth_results_raw
        dmarc_pass = "dmarc=pass" in auth_results_raw
    else:
        spf_pass = None
        dkim_pass = None
        dmarc_pass = None

    # Extract body content
    plain_text, html_text = extract_body_parts(payload)

    if plain_text and plain_text.strip():
        final_body = plain_text.strip()
        content_type_used = "text/plain"
    elif html_text and html_text.strip():
        final_body = html_to_plain_text(html_text).strip()
        content_type_used = "text/html"
    else:
        final_body = ""
        content_type_used = "empty"

    combined_text = combine_subject_and_body(subject, final_body)

    return ParsedEmail(
        message_id=msg_id,
        thread_id=thread_id,
        sender=sender,
        subject=subject,
        received_at=received_at,
        internal_date_ms=internal_date_ms,
        body=final_body,
        combined_text=combined_text,
        content_type_used=content_type_used,
        spf_pass=spf_pass,
        dkim_pass=dkim_pass,
        dmarc_pass=dmarc_pass,
    )
