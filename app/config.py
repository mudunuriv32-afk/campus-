import os
import socket
from urllib.parse import urlparse, urlunparse
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..'))
load_dotenv(os.path.join(project_root, '.env'))


def resolve_render_host(url: str) -> str:
    """If database URL has a bare Render internal host (e.g. dpg-xxxx-a) that fails to resolve, append region domain."""
    if not url or not url.startswith(('postgres://', 'postgresql://')):
        return url
    try:
        temp = url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url
        parsed = urlparse(temp)
        host = parsed.hostname
        if host and host.startswith('dpg-') and '.' not in host:
            try:
                socket.gethostbyname(host)
            except socket.gaierror:
                region = os.getenv('RENDER_REGION', 'oregon')
                candidates = [
                    f'{region}-postgres.render.com',
                    'oregon-postgres.render.com',
                    'frankfurt-postgres.render.com',
                    'ohio-postgres.render.com',
                    'singapore-postgres.render.com',
                    'virginia-postgres.render.com'
                ]
                for domain in candidates:
                    candidate_host = f'{host}.{domain}'
                    try:
                        socket.gethostbyname(candidate_host)
                        user = parsed.username or ''
                        pw = f':{parsed.password}' if parsed.password else ''
                        auth = f'{user}{pw}@' if (user or pw) else ''
                        port = f':{parsed.port}' if parsed.port else ''
                        new_netloc = f'{auth}{candidate_host}{port}'
                        parsed = parsed._replace(netloc=new_netloc)
                        return urlunparse(parsed)
                    except socket.gaierror:
                        continue
    except Exception:
        pass
    return url


def resolve_supabase_host(url: str) -> str:
    """If database URL uses direct Supabase host (db.[ref].supabase.co) that lacks IPv4 on Render,
    route to Supabase's IPv4 connection pooler."""
    if not url or 'supabase.co' not in url:
        return url
    try:
        temp = url.replace('postgres://', 'postgresql://', 1) if url.startswith('postgres://') else url
        parsed = urlparse(temp)
        host = parsed.hostname
        if host and host.startswith('db.') and host.endswith('.supabase.co'):
            try:
                # Check if host resolves on IPv4
                socket.gethostbyname(host)
            except socket.gaierror:
                # Direct domain has no IPv4 A record (IPv6 only).
                # Convert to Supabase IPv4 Connection Pooler
                project_ref = host.split('.')[1]
                pooler_host = os.getenv('SUPABASE_POOLER_HOST', 'aws-0-ap-northeast-2.pooler.supabase.com')
                user = parsed.username or 'postgres'
                if '.' not in user:
                    user = f"{user}.{project_ref}"
                pw = f":{parsed.password}" if parsed.password else ""
                auth = f"{user}{pw}@"
                port = f":{parsed.port}" if parsed.port else ":5432"
                new_netloc = f"{auth}{pooler_host}{port}"
                parsed = parsed._replace(netloc=new_netloc)
                return urlunparse(parsed)
    except Exception:
        pass
    return url


def get_database_url():
    """Get database URL with Render/Heroku/Supabase compatibility fix."""
    url = os.getenv('DATABASE_URL')
    if not url:
        instance_dir = os.path.join(project_root, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, 'campusconnect.db').replace('\\', '/')
        return f"sqlite:///{db_path}"
    if url.startswith("sqlite:///"):
        db_file = url.replace("sqlite:///", "", 1)
        if not os.path.isabs(db_file):
            db_file = os.path.join(project_root, db_file)
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
        return f"sqlite:///{os.path.abspath(db_file).replace('\\', '/')}"

    # Auto-resolve bare Render internal hostname (dpg-xxxx-a) if unresolvable
    url = resolve_render_host(url)

    # Auto-resolve Supabase direct host (db.[ref].supabase.co) to IPv4 pooler if host is IPv6-only
    url = resolve_supabase_host(url)

    # Detect available postgres driver (prefer psycopg v3, fallback to psycopg2)
    driver = "postgresql+psycopg"
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2
            driver = "postgresql+psycopg2"
        except ImportError:
            driver = "postgresql"

    if url.startswith("postgres://"):
        url = url.replace("postgres://", f"{driver}://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", f"{driver}://", 1)
    return url


class Config:
    """Base Configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'campusconnect-dev-key-90531c48-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = get_database_url()
    
    # File Uploads
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5MB max
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # Pagination
    ITEMS_PER_PAGE = 9
    
    # Cookies & Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Optional SMTP configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'notifications@campusconnect.edu')


class DevelopmentConfig(Config):
    """Development Configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing Configuration."""
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(project_root, 'instance', 'campusconnect_test.db').replace('\\', '/')}"
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'test_uploads')


class ProductionConfig(Config):
    """Production Configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # High concurrency connection pooling for 4,000+ members
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '25')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '50')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '300')),
        'pool_pre_ping': True
    }


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
