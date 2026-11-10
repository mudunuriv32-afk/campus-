"""
Anti-bot detection and defense service.
Filters automated scrapers, malicious vulnerability scanners, and automated spam submissions
using honeypot fields, User-Agent heuristic analysis, and security auditing.
"""
import re
from flask import request, current_app
from app.extensions import db
from app.models.audit import AuditLog

# Honeypot field name used across forms
HONEYPOT_FIELD_NAME = 'cc_website_hp'

# Known automated vulnerability scanners and malicious bot signatures
BAD_BOT_PATTERNS = [
    r'sqlmap',
    r'nikto',
    r'masscan',
    r'zgrab',
    r'censys',
    r'havij',
    r'acunetix',
    r'dirbuster',
    r'nmap',
    r'netsparker',
    r'wpscan',
    r'morfeus',
    r'arachni',
    r'gobuster',
    r'burpcollaborator',
]

_BAD_BOT_REGEX = re.compile('|'.join(BAD_BOT_PATTERNS), re.IGNORECASE)


def is_malicious_user_agent(user_agent: str) -> bool:
    """Check if User-Agent header matches known scanner/exploit bot patterns."""
    if not user_agent:
        return False
    return bool(_BAD_BOT_REGEX.search(user_agent))


def check_honeypot(req) -> bool:
    """
    Check if honeypot trap field was filled.
    Real human users and screen readers will never interact with this invisible field.
    Returns True if bot activity is detected (honeypot contains text), False otherwise.
    """
    if req.method in ('POST', 'PUT', 'PATCH'):
        honeypot_value = req.form.get(HONEYPOT_FIELD_NAME)
        if honeypot_value and honeypot_value.strip():
            return True
    return False


def validate_anti_bot(req) -> tuple[bool, str]:
    """
    Comprehensive anti-bot validation for requests.
    Returns (is_valid: bool, reason: str).
    """
    # 1. User-Agent check
    ua = req.headers.get('User-Agent', '')
    if is_malicious_user_agent(ua):
        return False, f"Malicious scanner User-Agent detected: '{ua[:50]}'"

    # 2. Honeypot check for form submissions
    if check_honeypot(req):
        return False, "Automated bot submission detected via honeypot trap"

    return True, "Valid request"


def log_bot_activity(req, reason: str, user_id: int = None):
    """Log blocked bot attempt in security audit trail."""
    try:
        AuditLog.log(
            action='BOT_BLOCKED',
            user_id=user_id,
            target_type='Security',
            target_id=None,
            ip_address=req.remote_addr,
            details=f"Blocked request from UA '{req.headers.get('User-Agent', '')[:60]}': {reason}"
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if current_app:
            current_app.logger.warning(f"Could not log bot activity to audit: {e}")
