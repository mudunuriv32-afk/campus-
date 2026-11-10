import re
import time
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, g
from app.models.user import User

# In-memory rate limiting store for sensitive endpoints (IP -> [timestamp, ...])
_RATE_LIMIT_STORE = {}


def check_rate_limit(key: str, limit: int = 5, window_seconds: int = 60, force_check: bool = False) -> bool:
    """Check if key has exceeded the rate limit. Returns True if allowed, False if exceeded."""
    from flask import current_app
    try:
        if current_app and current_app.config.get('TESTING') and not force_check:
            return True
    except RuntimeError:
        pass

    now = time.time()
    timestamps = _RATE_LIMIT_STORE.get(key, [])
    # Filter out timestamps older than window
    timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(timestamps) >= limit:
        _RATE_LIMIT_STORE[key] = timestamps
        return False
    timestamps.append(now)
    _RATE_LIMIT_STORE[key] = timestamps
    return True


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password complexity requirements."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, ""


def get_current_user():
    """Retrieve current logged-in user from session and cache in flask.g."""
    user_id = session.get('user_id')
    if not user_id:
        g.current_user = None
        g._current_user_id = None
        return None

    if getattr(g, '_current_user_id', None) != user_id:
        from app.extensions import db
        user = db.session.get(User, user_id)
        if user and user.is_active:
            g.current_user = user
            g._current_user_id = user_id
        else:
            session.clear()
            g.current_user = None
            g._current_user_id = None

    return g.current_user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        if user.force_password_change and request.endpoint not in ('auth.change_temporary_password', 'change_temporary_password_root', 'auth.logout'):
            flash("An administrator has reset your password. You must set a permanent password to continue.", "warning")
            return redirect(url_for('change_temporary_password_root'))
        return f(*args, **kwargs)
    return decorated_function


def roles_accepted(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.path))
            if user.force_password_change and request.endpoint not in ('auth.change_temporary_password', 'change_temporary_password_root', 'auth.logout'):
                flash("An administrator has reset your password. You must set a permanent password to continue.", "warning")
                return redirect(url_for('change_temporary_password_root'))
            if not user.has_role(*roles):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
