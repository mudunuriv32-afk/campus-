from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.items import items_bp
from app.routes.claims import claims_bp
from app.routes.dashboard import dashboard_bp
from app.routes.admin import admin_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'items_bp',
    'claims_bp',
    'dashboard_bp',
    'admin_bp'
]
