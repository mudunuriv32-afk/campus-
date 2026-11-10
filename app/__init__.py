import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, g, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import config_by_name
from app.extensions import db, migrate, csrf
from app.services.auth_service import get_current_user
from app.services.notification_service import get_unread_count
from app.services.bot_detection_service import is_malicious_user_agent, log_bot_activity


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Configure Reverse-Proxy / Load Balancer headers (ProxyFix)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Ensure all ORM models are registered
    from app import models

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'items'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'claims'), exist_ok=True)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.items import items_bp
    from app.routes.claims import claims_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    # Register root-level mandatory temporary password change route
    from app.routes.auth import change_temporary_password
    app.add_url_rule(
        '/change-temporary-password',
        endpoint='change_temporary_password_root',
        view_func=change_temporary_password,
        methods=['GET', 'POST']
    )

    # Template filter for cloud vs local media uploads
    @app.template_filter('media_url')
    def media_url_filter(path):
        if not path:
            return ''
        if path.startswith('http://') or path.startswith('https://'):
            return path
        return f"/static/uploads/{path}"

    # Context processors for all Jinja2 templates
    @app.context_processor
    def inject_global_template_vars():
        try:
            user = get_current_user()
            unread_count = get_unread_count(user.id) if user else 0
        except Exception:
            user = None
            unread_count = 0
        return {
            'current_user': user,
            'unread_notifications_count': unread_count,
            'current_year': datetime.now(timezone.utc).year,
            'app_name': 'CampusConnect',
            'media_url': media_url_filter
        }

    # Anti-Bot Middleware: Block known malicious scanners and exploit crawlers
    @app.before_request
    def filter_bad_bots():
        ua = request.headers.get('User-Agent', '')
        if is_malicious_user_agent(ua):
            log_bot_activity(request, "Blocked malicious scanner User-Agent")
            abort(403)

    # Security & Caching Headers Middleware
    @app.after_request
    def set_security_and_cache_headers(response):
        # OWASP Security Headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Performance & Caching Policy:
        # Static assets: 1-year immutable caching for maximum speed and zero server load
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        # Authenticated & sensitive state: never cache in browser or intermediate proxies
        elif any(request.path.startswith(p) for p in ('/dashboard', '/admin', '/auth', '/change-temporary-password')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Custom CLI commands for database setup & seed
    register_cli_commands(app)

    return app


def register_cli_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables and populate seed data (roles, departments, categories, demo accounts)."""
        with app.app_context():
            try:
                db.create_all()
                from app.seed import seed_database
                seed_database()
                print("Database initialized and populated with seed data successfully.")
            except Exception as e:
                print(f"[Notice] Database initialization deferred: {e}")
                print("[Notice] In Render build environment, database host may not be resolvable.")
                print("[Notice] Schema creation will automatically execute at runtime when Gunicorn boots.")

    @app.cli.command("seed-data")
    def seed_data_cmd():
        """Populate initial seed data."""
        with app.app_context():
            try:
                from app.seed import seed_database
                seed_database()
                print("Seed data applied successfully.")
            except Exception as e:
                print(f"[Notice] Seed data deferred: {e}")
