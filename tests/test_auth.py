import pytest
from app.models.user import User


def test_student_registration_success(client, app):
    """Test successful student account registration."""
    with app.app_context():
        dept = User.query.first().department_id
    
    response = client.post('/auth/register-student', data={
        'full_name': 'New Student User',
        'email': 'newstudent@campusconnect.edu',
        'campus_id': 'STU-9999',
        'department_id': dept,
        'designation_or_year': '1st Year Undergraduate',
        'phone': '+1-555-8888',
        'password': 'Password@123!',
        'confirm_password': 'Password@123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    with app.app_context():
        user = User.query.filter_by(email='newstudent@campusconnect.edu').first()
        assert user is not None
        assert user.is_active is True
        assert user.is_approved is True
        assert user.check_password('Password@123!')


def test_duplicate_registration_prevented(client, app):
    """Test that duplicate email and duplicate campus ID cannot register."""
    with app.app_context():
        dept = User.query.first().department_id

    response = client.post('/auth/register-student', data={
        'full_name': 'Duplicate Email User',
        'email': 'student@campusconnect.edu',  # Existing seed email
        'campus_id': 'STU-NEW-01',
        'department_id': dept,
        'designation_or_year': '2nd Year Undergraduate',
        'phone': '+1-555-7777',
        'password': 'Password@123!',
        'confirm_password': 'Password@123!'
    })

    assert b"already registered" in response.data


def test_password_strength_validation(client, app):
    """Test that weak passwords without uppercase or special symbols are rejected."""
    with app.app_context():
        dept = User.query.first().department_id

    response = client.post('/auth/register-student', data={
        'full_name': 'Weak Password User',
        'email': 'weakpwd@campusconnect.edu',
        'campus_id': 'STU-WEAK-01',
        'department_id': dept,
        'designation_or_year': '2nd Year Undergraduate',
        'phone': '+1-555-6666',
        'password': 'simplepassword',  # Missing upper, number, symbol
        'confirm_password': 'simplepassword'
    })

    assert b"Password must contain" in response.data


def test_login_success_and_logout(client):
    """Test successful login and subsequent logout."""
    res_login = client.post('/auth/login', data={
        'email': 'student@campusconnect.edu',
        'password': 'Student@2026!'
    }, follow_redirects=True)

    assert res_login.status_code == 200
    assert b"Welcome back" in res_login.data
    assert b"Sign Out" in res_login.data

    res_logout = client.get('/auth/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b"signed out safely" in res_logout.data


def test_login_invalid_credentials(client):
    """Test login failure with wrong password."""
    response = client.post('/auth/login', data={
        'email': 'student@campusconnect.edu',
        'password': 'WrongPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid college email or password" in response.data


def test_staff_registration_requires_approval(client, app):
    """Test staff registration puts account in unapproved state until admin verification."""
    with app.app_context():
        dept = User.query.first().department_id

    response = client.post('/auth/register-staff', data={
        'full_name': 'Dr. Pending Staff',
        'email': 'pendingstaff@campusconnect.edu',
        'campus_id': 'STF-PEND-01',
        'department_id': dept,
        'designation_or_year': 'Assistant Professor',
        'phone': '+1-555-3333',
        'password': 'Password@123!',
        'confirm_password': 'Password@123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"active once verified by an administrator" in response.data

    with app.app_context():
        user = User.query.filter_by(email='pendingstaff@campusconnect.edu').first()
        assert user is not None
        assert user.is_approved is False

    # Attempting to login before approval
    res_login = client.post('/auth/login', data={
        'email': 'pendingstaff@campusconnect.edu',
        'password': 'Password@123!'
    }, follow_redirects=True)
    assert b"pending administrative verification" in res_login.data


def test_role_based_access_control(client, auth_client):
    """Test that a student cannot access the admin blueprint."""
    auth_client('student@campusconnect.edu', 'Student@2026!')
    response = client.get('/admin/dashboard')
    assert response.status_code == 403
