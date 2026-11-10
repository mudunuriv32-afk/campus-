import io
import pytest
from app.services.upload_service import validate_and_save_image
from werkzeug.datastructures import FileStorage
from app.services.auth_service import check_rate_limit


def test_security_headers_present(client):
    """Verify production security headers on all HTTP responses."""
    res = client.get('/')
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert res.headers.get('X-XSS-Protection') == '1; mode=block'
    assert res.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


def test_health_check_endpoint(client):
    """Test health probe returns 200 without leaking credentials or internal directories."""
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'HEALTHY'
    assert data['database_connected'] is True
    # Ensure no credentials or keys are in health JSON
    assert 'SECRET_KEY' not in str(data)
    assert 'password' not in str(data)
    assert 'DATABASE_URL' not in str(data)


def test_disallowed_file_extension(app):
    """Ensure scripts or dangerous file types (.exe, .php, .sh, .py) are rejected."""
    with app.app_context():
        fake_file = FileStorage(
            stream=io.BytesIO(b"echo 'malicious script'"),
            filename="exploit.php",
            content_type="text/x-php"
        )
        success, msg = validate_and_save_image(fake_file)
        assert success is False
        assert "not allowed" in msg


def test_fake_image_magic_byte_rejected(app):
    """Test spoofed extension (e.g. executable disguised as .png) is rejected by Pillow verification."""
    with app.app_context():
        # Text file masquerading as a PNG
        fake_png = FileStorage(
            stream=io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00ThisIsNotAPNG"),
            filename="trojan.png",
            content_type="image/png"
        )
        success, msg = validate_and_save_image(fake_png)
        assert success is False
        assert "verification failed" in msg.lower() or "invalid" in msg.lower()


def test_rate_limiter_blocks_abuse():
    """Test rate limiter triggers after exceeding threshold."""
    key = "test_abuse_ip_127.0.0.1"
    # Allow 3 requests in 10 seconds
    for _ in range(3):
        assert check_rate_limit(key, limit=3, window_seconds=10, force_check=True) is True
    # 4th request must be blocked
    assert check_rate_limit(key, limit=3, window_seconds=10, force_check=True) is False
