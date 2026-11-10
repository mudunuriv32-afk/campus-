import pytest
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.user import User
from app.models.password_reset import PasswordResetRecord
from app.models.audit import AuditLog
from app.services.password_reset_service import (
    search_user_by_campus_id,
    initiate_admin_password_reset,
    complete_temporary_password_change
)


def test_01_admin_searches_existing_user_id(client, auth_client):
    """Scenario 1: Admin searches an existing User ID (College ID)."""
    # Login as admin
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    # Search existing student by College ID
    response = client.get('/admin/password-reset?college_id=STU-3001')
    assert response.status_code == 200
    assert b"Jordan Lee" in response.data
    assert b"STU-3001" in response.data
    assert b"student@campusconnect.edu" in response.data
    assert b"Generate Temporary Password" in response.data


def test_02_admin_searches_invalid_user_id(client, auth_client):
    """Scenario 2: Admin searches an invalid User ID."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    # Search nonexistent College ID
    response = client.get('/admin/password-reset?college_id=NONEXISTENT-9999')
    assert response.status_code == 200
    assert b"No user account found matching College ID" in response.data


def test_03_admin_generates_temporary_password(client, auth_client):
    """Scenario 3: Admin generates a temporary password with 15-minute expiry and audit log."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    student = User.query.filter_by(campus_id='STU-3001').first()
    assert student is not None
    original_pw_hash = student.password_hash

    # Admin posts to generate temporary password
    res = client.post('/admin/password-reset/generate', data={
        'user_id': student.id
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Temporary Password Generated Successfully" in res.data
    assert b"Copy Password" in res.data

    # Verify DB state
    db.session.refresh(student)
    assert student.force_password_change is True
    assert student.temp_password_hash is not None
    assert student.temp_password_expires_at is not None
    assert student.password_hash != original_pw_hash  # Previous permanent password invalidated

    # Verify audit log was recorded
    audit_entry = AuditLog.query.filter_by(action='ADMIN_PASSWORD_RESET', target_id=student.id).first()
    assert audit_entry is not None
    assert "STU-3001" in audit_entry.details

    # Verify reset record was stored
    reset_rec = PasswordResetRecord.query.filter_by(target_user_id=student.id, status='ACTIVE').first()
    assert reset_rec is not None
    assert reset_rec.is_expired is False


def test_04_user_logins_using_temporary_password(client, auth_client):
    """Scenario 4: User logs in using the temporary password (via College ID or email)."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    # Generate temporary password programmatically to get plain-text credential
    success, msg, temp_pw = initiate_admin_password_reset(admin, student, expires_in_minutes=15)
    assert success is True
    assert temp_pw is not None

    # Sign in using College ID and temporary password
    client.get('/auth/logout')
    login_res = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': temp_pw
    }, follow_redirects=True)

    assert login_res.status_code == 200
    # Must notify user about temporary sign-in and direct them to change password
    assert b"temporary password" in login_res.data
    assert b"Set Permanent Password" in login_res.data


def test_05_user_redirected_to_mandatory_password_change(client):
    """Scenario 5: User with force_password_change is strictly prevented from navigating elsewhere."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    _, _, temp_pw = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    # Login
    client.get('/auth/logout')
    login_post = client.post('/auth/login', data={'email': 'student@campusconnect.edu', 'password': temp_pw}, follow_redirects=False)
    assert login_post.status_code == 302
    assert '/change-temporary-password' in login_post.headers['Location']

    # Attempt to visit student dashboard directly
    res = client.get('/dashboard/student', follow_redirects=False)
    assert res.status_code == 302
    assert '/change-temporary-password' in res.headers['Location']

    # Attempt to visit protected report-lost page directly
    res2 = client.get('/items/report-lost', follow_redirects=False)
    assert res2.status_code == 302
    assert '/change-temporary-password' in res2.headers['Location']


def test_06_user_changes_password_successfully(client):
    """Scenario 6: User changes the password successfully and gains normal dashboard access."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    _, _, temp_pw = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    client.get('/auth/logout')
    client.post('/auth/login', data={'email': 'STU-3001', 'password': temp_pw}, follow_redirects=True)

    # Submit password change
    new_secret = 'MyPermanent2026!Pass'
    res = client.post('/change-temporary-password', data={
        'temp_password': temp_pw,
        'new_password': new_secret,
        'confirm_password': new_secret
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Your permanent password has been set successfully" in res.data
    assert b"Student Dashboard" in res.data or b"Jordan Lee" in res.data

    # Verify user can now log in normally with new password
    client.get('/auth/logout')
    login_after = client.post('/auth/login', data={
        'email': 'student@campusconnect.edu',
        'password': new_secret
    }, follow_redirects=True)
    assert login_after.status_code == 200
    assert b"Welcome back" in login_after.data

    # Check reset record marked completed
    rec = PasswordResetRecord.query.filter_by(target_user_id=student.id).order_by(PasswordResetRecord.id.desc()).first()
    assert rec.status == 'COMPLETED'
    assert rec.completed_at is not None


def test_07_user_cannot_reuse_temporary_password(client):
    """Scenario 7: User cannot reuse the temporary password as the new permanent password."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    _, _, temp_pw = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    client.get('/auth/logout')
    client.post('/auth/login', data={'email': 'student@campusconnect.edu', 'password': temp_pw}, follow_redirects=True)

    # Try setting new password to the temporary password
    res = client.post('/change-temporary-password', data={
        'temp_password': temp_pw,
        'new_password': temp_pw,
        'confirm_password': temp_pw
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"New password cannot be identical to your temporary password" in res.data


def test_08_expired_temporary_password_rejected(client):
    """Scenario 8: Expired temporary password is rejected on login attempt."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    # Generate temporary password with -1 minute expiry (already expired)
    _, _, temp_pw = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    # Manually backdate expiry in DB
    student.temp_password_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.session.add(student)
    db.session.commit()

    client.get('/auth/logout')
    res = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': temp_pw
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"expired" in res.data.lower()


def test_09_previous_temp_password_invalid_after_another_reset(client):
    """Scenario 9: Previous temporary password becomes invalid after another reset is triggered."""
    admin = User.query.filter_by(email='admin@campusconnect.edu').first()
    student = User.query.filter_by(campus_id='STU-3001').first()

    # First reset
    _, _, temp_pw_1 = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    # Second reset
    _, _, temp_pw_2 = initiate_admin_password_reset(admin, student, expires_in_minutes=15)

    client.get('/auth/logout')

    # Try signing in with first temporary password -> must fail
    res1 = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': temp_pw_1
    }, follow_redirects=True)
    assert b"Invalid college email or password" in res1.data

    # Sign in with second temporary password -> succeeds
    res2 = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': temp_pw_2
    }, follow_redirects=True)
    assert b"Set Permanent Password" in res2.data


def test_10_student_cannot_access_admin_reset_portal(client, auth_client):
    """Scenario 10: Student cannot access the admin reset portal (HTTP 403 / Forbidden)."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    res = client.get('/admin/password-reset')
    assert res.status_code in (403, 302)

    res_post = client.post('/admin/password-reset/generate', data={'user_id': 1})
    assert res_post.status_code in (403, 302)


def test_11_staff_cannot_access_reset_portal_without_admin_role(client, auth_client):
    """Scenario 11: Staff cannot access the reset portal without admin role (HTTP 403)."""
    auth_client('staff@campusconnect.edu', 'Staff@2026!')

    res = client.get('/admin/password-reset')
    assert res.status_code in (403, 302)

    res_post = client.post('/admin/password-reset/generate', data={'user_id': 1})
    assert res_post.status_code in (403, 302)


def test_12_admin_reset_history_recorded_correctly(client, auth_client):
    """Scenario 12: Admin reset history is recorded with correct attributes and non-plaintext credentials."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    student = User.query.filter_by(campus_id='STU-3002').first()
    assert student is not None

    # Generate reset
    client.post('/admin/password-reset/generate', data={'user_id': student.id}, follow_redirects=True)

    # Check reset history page
    res = client.get('/admin/password-reset')
    assert res.status_code == 200
    assert b"Administrative Password Reset History" in res.data
    assert b"STU-3002" in res.data
    assert b"Samantha Patel" in res.data
    assert b"ACTIVE" in res.data

    # Verify no plain-text passwords in DB record
    rec = PasswordResetRecord.query.filter_by(target_user_id=student.id).first()
    assert rec is not None
    assert rec.status == 'ACTIVE'
    # Ensure no password attribute exists on PasswordResetRecord
    assert not hasattr(rec, 'password')
    assert not hasattr(rec, 'temp_password')


def test_13_login_with_college_id(client):
    """Verify students can sign in with College ID directly."""
    client.get('/auth/logout')
    res = client.post('/auth/login', data={
        'email': 'STU-3001',
        'password': 'Student@2026!'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back, Jordan Lee!" in res.data


def test_14_student_profile_photo_upload_and_immutable_campus_id(client, auth_client, sample_image):
    """Verify student profile view, photo upload validation, and immutable College ID."""
    auth_client('student@campusconnect.edu', 'Student@2026!')

    # Access profile
    res = client.get('/dashboard/profile')
    assert res.status_code == 200
    assert b"Jordan Lee" in res.data
    assert b"STU-3001" in res.data
    assert b"Institutional Student Identity" in res.data

    # Upload valid profile photo
    res_upload = client.post('/dashboard/profile', data={
        'photo': (sample_image, 'my_avatar.png')
    }, content_type='multipart/form-data', follow_redirects=True)

    assert res_upload.status_code == 200
    assert b"Profile photo updated successfully" in res_upload.data

    student = User.query.filter_by(campus_id='STU-3001').first()
    assert student.profile_photo is not None
    assert student.profile_photo.startswith('profiles/')
