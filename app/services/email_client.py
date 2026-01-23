"""
NEXUS Email Client
Connect to Gmail and iCloud via IMAP.
"""

import imaplib
import smtplib
import ssl
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, formatdate
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from ..config import settings
from ..exceptions.manual_tasks import ConfigurationInterventionRequired

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
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
        "email_env": "gmail_email",
        "password_env": "gmail_app_password"
    },
    "icloud": {
        "imap_server": "imap.mail.me.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.me.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
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
            except (UnicodeDecodeError, LookupError):
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
                except (UnicodeDecodeError, LookupError, ValueError):
                    continue
            elif content_type == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    is_html = True
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
            is_html = msg.get_content_type() == "text/html"
        except Exception:
            body = str(msg.get_payload())

    # Clean HTML if needed
    if is_html:
        # Basic HTML tag removal for preview
        body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<[^>]+>', ' ', body)
        body = re.sub(r'\s+', ' ', body).strip()

    return body, is_html


def connect_imap(account: str) -> imaplib.IMAP4_SSL:
    """Connect to IMAP server."""
    config = EMAIL_ACCOUNTS.get(account)
    if not config:
        logger.error(f"Unknown email account: {account}")
        raise ConfigurationInterventionRequired(
            description=f"Unknown email account '{account}'. Valid accounts: {list(EMAIL_ACCOUNTS.keys())}",
            title=f"Configure Email Account: {account}",
            source_system="service:email_client",
            context={"account": account, "valid_accounts": list(EMAIL_ACCOUNTS.keys())}
        )

    email_addr = getattr(settings, config["email_env"], None)
    password = getattr(settings, config["password_env"], None)

    if not email_addr or not password:
        logger.warning(f"Credentials not configured for {account}")
        env_var_name = config["email_env"] if not email_addr else config["password_env"]
        missing_cred = "email address" if not email_addr else "app password"
        raise ConfigurationInterventionRequired(
            description=f"{missing_cred.capitalize()} not configured for {account}. Add {env_var_name} to .env file",
            title=f"Configure {account.capitalize()} Credentials",
            source_system="service:email_client",
            context={"account": account, "missing_env_var": env_var_name, "missing_credential": missing_cred}
        )

    try:
        imap = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])
        imap.login(email_addr, password)
        logger.info(f"Connected to {account}")
        return imap
    except Exception as e:
        logger.error(f"Failed to connect to {account}: {e}")
        raise ConfigurationInterventionRequired(
            description=f"Failed to connect to {account}: {str(e)}. Check app password and internet connection.",
            title=f"Email Connection Failed: {account}",
            source_system="service:email_client",
            context={"account": account, "error": str(e), "server": config["imap_server"], "port": config["imap_port"]}
        )


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
                except Exception:
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
        except Exception:
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
        except Exception:
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
        except Exception:
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
        except Exception:
            pass


async def send_email(
    account: str,
    to_addresses: List[str],
    subject: str,
    body: str,
    cc_addresses: Optional[List[str]] = None,
    bcc_addresses: Optional[List[str]] = None,
    is_html: bool = False,
    reply_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email using SMTP.

    Args:
        account: 'gmail' or 'icloud'
        to_addresses: List of recipient email addresses
        subject: Email subject
        body: Email body content
        cc_addresses: Optional CC recipients
        bcc_addresses: Optional BCC recipients
        is_html: Whether body is HTML (default: False)
        reply_to: Optional reply-to address

    Returns:
        Dictionary with success status and message ID
    """
    config = EMAIL_ACCOUNTS.get(account)
    if not config:
        logger.error(f"Unknown email account: {account}")
        return {"success": False, "error": f"Unknown account: {account}"}

    email_addr = getattr(settings, config["email_env"], None)
    password = getattr(settings, config["password_env"], None)

    if not email_addr or not password:
        logger.warning(f"Credentials not configured for {account}")
        return {"success": False, "error": f"Credentials not configured for {account}"}

    smtp_server = config.get("smtp_server")
    smtp_port = config.get("smtp_port", 587)
    smtp_use_tls = config.get("smtp_use_tls", True)
    smtp_use_ssl = config.get("smtp_use_ssl", False)

    if not smtp_server:
        logger.error(f"SMTP server not configured for {account}")
        return {"success": False, "error": f"SMTP server not configured for {account}"}

    # Create message
    msg = MIMEMultipart('alternative' if is_html else 'mixed')
    msg['From'] = email_addr
    msg['To'] = ', '.join(to_addresses)
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)

    if cc_addresses:
        msg['Cc'] = ', '.join(cc_addresses)

    if reply_to:
        msg['Reply-To'] = reply_to

    # Add body
    body_part = MIMEText(body, 'html' if is_html else 'plain', 'utf-8')
    msg.attach(body_part)

    # Combine all recipients
    all_recipients = to_addresses.copy()
    if cc_addresses:
        all_recipients.extend(cc_addresses)
    if bcc_addresses:
        all_recipients.extend(bcc_addresses)

    try:
        # Connect to SMTP server
        if smtp_use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)

        # Start TLS if requested (and not using SSL)
        if smtp_use_tls and not smtp_use_ssl:
            server.starttls()

        # Login
        server.login(email_addr, password)

        # Send email
        server.sendmail(email_addr, all_recipients, msg.as_string())
        server.quit()

        # Generate a simple message ID for tracking
        message_id = f"<{datetime.now().timestamp()}.{email_addr}>"

        logger.info(f"Email sent successfully from {account} to {len(all_recipients)} recipients")
        return {
            "success": True,
            "message_id": message_id,
            "account": account,
            "recipients": all_recipients
        }

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"success": False, "error": str(e)}
