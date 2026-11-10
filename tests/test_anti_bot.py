"""
Test suite for Anti-Bot Protection, Honeypot Trap, and Malicious User-Agent Blocking.
"""
import pytest
from app.models.audit import AuditLog
from app.services.bot_detection_service import is_malicious_user_agent, check_honeypot


def test_malicious_user_agent_detection():
    """Verify scanner and exploit bot User-Agents are identified."""
    assert is_malicious_user_agent("sqlmap/1.5#stable (http://sqlmap.org)") is True
    assert is_malicious_user_agent("Mozilla/5.0 Nikto/2.1.6") is True
    assert is_malicious_user_agent("masscan/1.0 (https://github.com/robertdavidgraham/masscan)") is True
    assert is_malicious_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36") is False


def test_malicious_user_agent_blocked_by_middleware(client):
    """Verify middleware returns HTTP 403 when a malicious scanner User-Agent requests the app."""
    response = client.get('/', headers={'User-Agent': 'sqlmap/1.5-dev'})
    assert response.status_code == 403

    # Legitimate browser passes
    legit_response = client.get('/', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert legit_response.status_code == 200


def test_honeypot_trap_blocks_automated_bot_submission(client):
    """Verify submitting a form with honeypot field filled triggers HTTP 400 Bad Request."""
    # Bot fills all fields including invisible cc_website_hp
    bot_payload = {
        'email': 'bot@automated-spam.com',
        'password': 'AnyPassword123!',
        'cc_website_hp': 'http://buy-cheap-spam.ru'
    }
    response = client.post('/auth/login', data=bot_payload)
    assert response.status_code == 400

    # Verify security audit log recorded the blocked bot
    with client.application.app_context():
        bot_log = AuditLog.query.filter_by(action='BOT_BLOCKED').order_by(AuditLog.id.desc()).first()
        assert bot_log is not None
        assert 'honeypot' in bot_log.details.lower()


def test_clean_submission_without_honeypot_passes(client):
    """Verify human user submission without honeypot is processed normally."""
    clean_payload = {
        'email': 'student@campusconnect.edu',
        'password': 'WrongPassword123!',
        'cc_website_hp': ''
    }
    response = client.post('/auth/login', data=clean_payload, follow_redirects=True)
    # Reaches authentication verification rather than bot block
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data or b"Sign In" in response.data
