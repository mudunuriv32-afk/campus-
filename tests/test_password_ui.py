"""
Test suite for Password Check Icon / Match Validation, Dual Login, and Universal Refresh Button.
"""
import pytest
from app.extensions import db
from app.models.user import User


def test_dual_login_with_college_id(client):
    """Verify students can sign in using official Student/Campus ID."""
    response = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': 'Student@2026!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Jordan Lee!" in response.data or b"Student Dashboard" in response.data


def test_dual_login_with_college_email(client):
    """Verify students can sign in using official College Email."""
    response = client.post('/auth/login', data={
        'email': 'student@campusconnect.edu',
        'password': 'Student@2026!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Jordan Lee!" in response.data or b"Student Dashboard" in response.data


def test_dual_login_case_insensitive_and_whitespace_trimmed(client):
    """Verify login handles case-insensitivity and surrounding whitespace."""
    response = client.post('/auth/login', data={
        'email': '  stu-3001  ',
        'password': 'Student@2026!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back" in response.data or b"Student Dashboard" in response.data


def test_registration_password_mismatch_rejected(client):
    """Verify student registration rejects mismatched passwords."""
    response = client.post('/auth/register-student', data={
        'full_name': 'Test New Student',
        'email': 'testnewstudent@campusconnect.edu',
        'campus_id': 'STU-9999',
        'department_id': 1,
        'designation_or_year': '3rd Year Undergraduate',
        'phone': '+1 (555) 987-6543',
        'password': 'ValidPassword@2026!',
        'confirm_password': 'MismatchedPassword@2026!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Passwords must match" in response.data or b"is-invalid" in response.data


def test_change_password_mismatch_rejected(client):
    """Verify change password rejects mismatched confirm password."""
    # Login as student first
    client.post('/auth/login', data={
        'email': 'student@campusconnect.edu',
        'password': 'Student@2026!'
    }, follow_redirects=True)

    response = client.post('/auth/change-password', data={
        'old_password': 'Student@2026!',
        'new_password': 'NewPassword@2026!',
        'confirm_password': 'DifferentPassword@2026!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Passwords must match" in response.data or b"is-invalid" in response.data


def test_universal_refresh_button_rendered(client):
    """Verify universal refresh button is present in the navigation bar across pages."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'id="globalRefreshBtn"' in response.data
    assert b'bi-arrow-clockwise' in response.data
