import secrets
import string
from datetime import datetime, timezone, timedelta
from flask import request, has_request_context
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.password_reset import PasswordResetRecord
from app.models.audit import AuditLog
from app.services.auth_service import validate_password_strength


def generate_secure_temporary_password(length: int = 12) -> str:
    """Generate a cryptographically secure random temporary password meeting all complexity rules."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    while True:
        # Guarantee inclusion of at least one char from each set
        upper = secrets.choice(string.ascii_uppercase)
        lower = secrets.choice(string.ascii_lowercase)
        digit = secrets.choice(string.digits)
        special = secrets.choice("!@#$%^&*()")
        middle = "".join(secrets.choice(chars) for _ in range(max(4, length - 4)))
        candidate_list = list(upper + lower + digit + special + middle)
        secrets.SystemRandom().shuffle(candidate_list)
        candidate = "".join(candidate_list)
        is_valid, _ = validate_password_strength(candidate)
        if is_valid:
            return candidate


def search_user_by_campus_id(campus_id: str) -> User | None:
    """Case-insensitive search for a user by College ID / Employee ID (campus_id)."""
    if not campus_id:
        return None
    cleaned = campus_id.strip()
    return User.query.filter(func.upper(User.campus_id) == cleaned.upper()).first()


def initiate_admin_password_reset(admin_user: User, target_user: User, expires_in_minutes: int = 15) -> tuple[bool, str, str | None]:
    """
    Generate temporary password, invalidate current password, and record audit trail.
    Returns (success, message, plain_temporary_password).
    """
    if not target_user:
        return False, "Target user not found.", None

    if not target_user.is_active:
        return False, "Cannot reset password for a deactivated account. Please activate the user first.", None

    # Supersede any currently active reset records for this user
    PasswordResetRecord.query.filter_by(
        target_user_id=target_user.id,
        status='ACTIVE'
    ).update({'status': 'SUPERSEDED'}, synchronize_session=False)

    # Generate temporary password
    temp_pw = generate_secure_temporary_password(12)
    target_user.set_temp_password(temp_pw, expires_in_minutes=expires_in_minutes)
    db.session.add(target_user)

    # Create password reset record
    record = PasswordResetRecord(
        target_user_id=target_user.id,
        admin_id=admin_user.id,
        reset_timestamp=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        status='ACTIVE'
    )
    db.session.add(record)

    # Log audit entry (NEVER log the plain-text password)
    ip_addr = request.remote_addr if has_request_context() else None
    AuditLog.log(
        action='ADMIN_PASSWORD_RESET',
        user_id=admin_user.id,
        target_type='User',
        target_id=target_user.id,
        ip_address=ip_addr,
        details=f"Admin {admin_user.email} generated temporary password for user {target_user.campus_id} ({target_user.full_name}). Expiry: {expires_in_minutes} minutes."
    )

    db.session.commit()
    return True, f"Temporary password generated for {target_user.full_name} ({target_user.campus_id}).", temp_pw


def complete_temporary_password_change(user: User, temp_password: str, new_password: str) -> tuple[bool, str]:
    """
    Verify temporary password, validate new password rules and anti-reuse, and update permanently.
    """
    if not user:
        return False, "User not found."

    # Verify temporary password
    is_valid, msg = user.verify_temp_password(temp_password)
    if not is_valid:
        return False, msg

    # Anti-reuse: prevent new password from being the temporary password
    if new_password == temp_password:
        return False, "New password cannot be identical to your temporary password."

    # Validate password complexity
    strength_valid, strength_msg = validate_password_strength(new_password)
    if not strength_valid:
        return False, strength_msg

    # Set new permanent password and clear temporary state
    user.set_password(new_password)
    user.clear_temp_password()
    db.session.add(user)

    # Mark active reset record as COMPLETED
    active_record = PasswordResetRecord.query.filter_by(
        target_user_id=user.id,
        status='ACTIVE'
    ).order_by(PasswordResetRecord.reset_timestamp.desc()).first()

    if active_record:
        active_record.status = 'COMPLETED'
        active_record.completed_at = datetime.now(timezone.utc)

    ip_addr = request.remote_addr if has_request_context() else None
    AuditLog.log(
        action='USER_TEMP_PASSWORD_CHANGED',
        user_id=user.id,
        target_type='User',
        target_id=user.id,
        ip_address=ip_addr,
        details=f"User {user.campus_id} ({user.email}) successfully completed mandatory password change."
    )

    db.session.commit()
    return True, "Your permanent password has been set successfully. Welcome to CampusConnect!"


def get_reset_history(page: int = 1, per_page: int = 15):
    """Retrieve paginated reset records and update expired active records."""
    now = datetime.now(timezone.utc)
    
    # Auto-expire active records whose expires_at has passed
    expired_query = PasswordResetRecord.query.filter(
        PasswordResetRecord.status == 'ACTIVE',
        PasswordResetRecord.expires_at < now
    )
    for exp_rec in expired_query.all():
        exp_rec.status = 'EXPIRED'
    db.session.commit()

    return PasswordResetRecord.query.order_by(
        PasswordResetRecord.reset_timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
