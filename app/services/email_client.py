"""
NEXUS Email Client
Connect to Gmail and iCloud via IMAP.
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Parsed email message."""
    message_id: str
    account: str
    sender: str
    sender_name: str
    recipient: str
    subject: str
    body: str
    body_preview: str
    received_at: datetime
    is_html: bool = False


# Email account configurations
EMAIL_ACCOUNTS = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "email_env": "gmail_email",
        "password_env": "gmail_app_password"
    },
    "icloud": {
        "imap_server": "imap.mail.me.com",
        "imap_port": 993,
        "email_env": "icloud_email",
        "password_env": "icloud_app_password"
    }
}


def decode_mime_header(header: str) -> str:
    """Decode MIME encoded header."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(encoding or 'utf-8', errors='replace'))
            except:
                result.append(part.decode('utf-8', errors='replace'))
        else:
            result.append(part)
    return ' '.join(result)


def extract_email_address(from_header: str) -> tuple:
    """Extract name and email from From header."""
    # Pattern: "Name" <email@domain.com> or just email@domain.com
    match = re.match(r'^"?([^"<]*)"?\s*<?([^>]+@[^>]+)>?$', from_header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email_addr = match.group(2).strip()
        return name or email_addr.split('@')[0], email_addr
    return from_header, from_header


def get_email_body(msg) -> tuple:
    """Extract body from email message. Returns (body, is_html)."""
    body = ""
    is_html = False

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    is_html = False
                    break  # Prefer plain text
                except:
                    continue
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    is_html = True
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
            is_html = msg.get_content_type() == "text/html"
        except:
            body = str(msg.get_payload())

    # Clean HTML if needed
    if is_html:
        # Basic HTML tag removal for preview
        body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<[^>]+>', ' ', body)
        body = re.sub(r'\s+', ' ', body).strip()

    return body, is_html


def connect_imap(account: str) -> Optional[imaplib.IMAP4_SSL]:
    """Connect to IMAP server."""
    config = EMAIL_ACCOUNTS.get(account)
    if not config:
        logger.error(f"Unknown email account: {account}")
        return None

    email_addr = getattr(settings, config["email_env"], None)
    password = getattr(settings, config["password_env"], None)

    if not email_addr or not password:
        logger.warning(f"Credentials not configured for {account}")
        return None

    try:
        imap = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])
        imap.login(email_addr, password)
        logger.info(f"Connected to {account}")
        return imap
    except Exception as e:
        logger.error(f"Failed to connect to {account}: {e}")
        return None


async def fetch_emails(
    account: str = "gmail",
    folder: str = "INBOX",
    since_days: int = 1,
    limit: int = 50
) -> List[EmailMessage]:
    """
    Fetch emails from an account.

    Args:
        account: 'gmail' or 'icloud'
        folder: IMAP folder name
        since_days: Fetch emails from last N days
        limit: Maximum emails to fetch

    Returns:
        List of EmailMessage objects
    """
    imap = connect_imap(account)
    if not imap:
        return []

    emails = []

    try:
        # Select folder
        status, _ = imap.select(folder)
        if status != "OK":
            logger.error(f"Failed to select folder {folder}")
            return []

        # Search for recent emails
        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        status, message_ids = imap.search(None, f'(SINCE {since_date})')

        if status != "OK":
            logger.error("Failed to search emails")
            return []

        ids = message_ids[0].split()
        # Get most recent first, limited
        ids = ids[-limit:][::-1]

        logger.info(f"Found {len(ids)} emails in {account}/{folder}")

        for msg_id in ids:
            try:
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Parse headers
                subject = decode_mime_header(msg.get("Subject", ""))
                from_header = decode_mime_header(msg.get("From", ""))
                to_header = decode_mime_header(msg.get("To", ""))
                message_id = msg.get("Message-ID", "")
                date_header = msg.get("Date", "")

                sender_name, sender_email = extract_email_address(from_header)

                # Parse date
                try:
                    received_at = parsedate_to_datetime(date_header)
                except:
                    received_at = datetime.now()

                # Get body
                body, is_html = get_email_body(msg)
                body_preview = body[:500] if body else ""

                emails.append(EmailMessage(
                    message_id=message_id,
                    account=account,
                    sender=sender_email,
                    sender_name=sender_name,
                    recipient=to_header,
                    subject=subject,
                    body=body,
                    body_preview=body_preview,
                    received_at=received_at,
                    is_html=is_html
                ))

            except Exception as e:
                logger.error(f"Failed to parse email {msg_id}: {e}")
                continue

    finally:
        try:
            imap.logout()
        except:
            pass

    return emails


async def fetch_all_accounts(
    since_days: int = 1,
    limit_per_account: int = 25
) -> List[EmailMessage]:
    """Fetch emails from all configured accounts."""
    all_emails = []

    for account in EMAIL_ACCOUNTS.keys():
        try:
            emails = await fetch_emails(
                account=account,
                since_days=since_days,
                limit=limit_per_account
            )
            all_emails.extend(emails)
        except Exception as e:
            logger.error(f"Failed to fetch from {account}: {e}")

    # Sort by date, newest first
    all_emails.sort(key=lambda x: x.received_at, reverse=True)

    return all_emails


async def archive_email(account: str, message_id: str) -> bool:
    """Archive an email (move to Archive/All Mail)."""
    imap = connect_imap(account)
    if not imap:
        return False

    try:
        imap.select("INBOX")

        # Find the email by Message-ID
        status, data = imap.search(None, f'(HEADER Message-ID "{message_id}")')
        if status != "OK" or not data[0]:
            return False

        msg_num = data[0].split()[0]

        # Gmail uses different archive folder
        if account == "gmail":
            # Just remove from INBOX (goes to All Mail)
            imap.store(msg_num, '+FLAGS', '\\Deleted')
            imap.expunge()
        else:
            # Move to Archive folder
            imap.copy(msg_num, "Archive")
            imap.store(msg_num, '+FLAGS', '\\Deleted')
            imap.expunge()

        return True

    except Exception as e:
        logger.error(f"Failed to archive email: {e}")
        return False

    finally:
        try:
            imap.logout()
        except:
            pass


async def delete_email(account: str, message_id: str) -> bool:
    """Delete an email (move to Trash)."""
    imap = connect_imap(account)
    if not imap:
        return False

    try:
        imap.select("INBOX")

        status, data = imap.search(None, f'(HEADER Message-ID "{message_id}")')
        if status != "OK" or not data[0]:
            return False

        msg_num = data[0].split()[0]

        # Move to Trash
        trash_folder = "[Gmail]/Trash" if account == "gmail" else "Trash"
        imap.copy(msg_num, trash_folder)
        imap.store(msg_num, '+FLAGS', '\\Deleted')
        imap.expunge()

        return True

    except Exception as e:
        logger.error(f"Failed to delete email: {e}")
        return False

    finally:
        try:
            imap.logout()
        except:
            pass


async def mark_as_read(account: str, message_id: str) -> bool:
    """Mark an email as read."""
    imap = connect_imap(account)
    if not imap:
        return False

    try:
        imap.select("INBOX")

        status, data = imap.search(None, f'(HEADER Message-ID "{message_id}")')
        if status != "OK" or not data[0]:
            return False

        msg_num = data[0].split()[0]
        imap.store(msg_num, '+FLAGS', '\\Seen')

        return True

    except Exception as e:
        logger.error(f"Failed to mark as read: {e}")
        return False

    finally:
        try:
            imap.logout()
        except:
            pass
