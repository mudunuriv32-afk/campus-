import pytest
from app.models.user import User, Role
from app.models.item import Item, ItemCategory
from app.models.claim import Claim
from app.models.audit import AuditLog
from app.models.settings import PlatformSetting


def test_admin_dashboard_access(client, auth_client):
    """Test administrator can access dashboard and metrics."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')
    res = client.get('/admin/dashboard')
    assert res.status_code == 200
    assert b"Campus Oversight Portal" in res.data
    assert b"Total Users" in res.data


def test_admin_toggle_user_status(client, auth_client, app):
    """Test admin can deactivate and reactivate student account."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    with app.app_context():
        target_user = User.query.filter_by(email='student@campusconnect.edu').first()
        target_id = target_user.id
        assert target_user.is_active is True

    # Deactivate
    res_deact = client.post(f'/admin/users/{target_id}/toggle-status', follow_redirects=True)
    assert res_deact.status_code == 200
    assert b"is now deactivated" in res_deact.data

    with app.app_context():
        u = User.query.get(target_id)
        assert u.is_active is False

    # Reactivate
    res_act = client.post(f'/admin/users/{target_id}/toggle-status', follow_redirects=True)
    assert res_act.status_code == 200
    assert b"is now activated" in res_act.data

    with app.app_context():
        u = User.query.get(target_id)
        assert u.is_active is True


def test_admin_cannot_deactivate_self(client, auth_client, app):
    """Test admin cannot deactivate their own root account."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    with app.app_context():
        admin = User.query.filter_by(email='admin@campusconnect.edu').first()
        admin_id = admin.id

    res = client.post(f'/admin/users/{admin_id}/toggle-status', follow_redirects=True)
    assert b"cannot deactivate your own" in res.data


def test_admin_approve_staff(client, auth_client, app):
    """Test admin approving a pending staff account."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    with app.app_context():
        staff_user = User.query.filter_by(email='pendingstaff@campusconnect.edu').first()
        if not staff_user:
            staff_role = Role.query.filter_by(name='staff').first()
            from app.extensions import db
            staff_user = User(
                email='staff2@campusconnect.edu',
                full_name='Staff Two',
                campus_id='STF-8822',
                phone='12345678',
                role_id=staff_role.id,
                department_id=1,
                designation_or_year='Lecturer',
                is_active=True,
                is_approved=False
            )
            staff_user.set_password('Password@123!')
            db.session.add(staff_user)
            db.session.commit()
        user_id = staff_user.id

    res = client.post(f'/admin/users/{user_id}/approve-staff', follow_redirects=True)
    assert res.status_code == 200
    assert b"approved successfully" in res.data

    with app.app_context():
        u = User.query.get(user_id)
        assert u.is_approved is True


def test_admin_item_moderation_unflag(client, auth_client, app):
    """Test admin unflagging and restoring a flagged item."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    with app.app_context():
        from app.extensions import db
        item = Item.query.first()
        item.status = 'FLAGGED'
        item.flagged_reason = 'Needs review'
        db.session.commit()
        item_id = item.id

    res = client.post(f'/admin/items/{item_id}/moderate', data={'action': 'UNFLAG'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"restored to OPEN status" in res.data

    with app.app_context():
        u_item = Item.query.get(item_id)
        assert u_item.status == 'OPEN'


def test_admin_create_category(client, auth_client, app):
    """Test admin adding a new category."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    res = client.post('/admin/categories', data={
        'name': 'Musical Instruments',
        'icon': 'bi-music-note',
        'description': 'Guitars, violin cases, flutes, audio gear'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Musical Instruments" in res.data

    with app.app_context():
        cat = ItemCategory.query.filter_by(name='Musical Instruments').first()
        assert cat is not None


def test_admin_audit_logs_recording(client, auth_client, app):
    """Test that administrative actions are captured in audit logs."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')
    res = client.get('/admin/audit-logs')
    assert res.status_code == 200
    assert b"System Audit Trail" in res.data

    with app.app_context():
        count = AuditLog.query.count()
        assert count > 0


def test_admin_settings_update(client, auth_client, app):
    """Test saving platform parameters."""
    auth_client('admin@campusconnect.edu', 'Admin@2026!')

    res = client.post('/admin/settings', data={
        'campus_name': 'Imperial Institute of Technology',
        'security_office_location': 'North Gate Desk #4',
        'support_email': 'security@campusconnect.edu',
        'retention_period_days': '120',
        'require_staff_approval': 'True'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Platform configuration saved successfully" in res.data

    with app.app_context():
        assert PlatformSetting.get('campus_name') == 'Imperial Institute of Technology'
        assert PlatformSetting.get('retention_period_days') == '120'
