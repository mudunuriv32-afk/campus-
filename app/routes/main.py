from flask import Blueprint, render_template, request, jsonify, current_app
from app.extensions import db
from app.models.item import Item, ItemCategory
from app.models.claim import Claim
from app.models.user import User
from app.services.cache_service import cache

main_bp = Blueprint('main', __name__)


def _get_platform_stats():
    try:
        return {
            'total_reported': Item.query.count(),
            'total_returned': Item.query.filter_by(status='RETURNED').count(),
            'total_users': User.query.filter_by(is_active=True).count(),
            'active_listings': Item.query.filter_by(status='OPEN').count()
        }
    except Exception as e:
        current_app.logger.warning(f"Stats query fallback: {e}")
        return {
            'total_reported': 0,
            'total_returned': 0,
            'total_users': 0,
            'active_listings': 0
        }


@main_bp.route('/')
def index():
    try:
        # Fetch platform stats with high-performance in-memory cache (TTL 3 minutes)
        stats = cache.get_or_set('stats:landing', _get_platform_stats, ttl=180)

        # Recent lost and found items (up to 4 each)
        recent_lost = Item.query.filter_by(item_type='LOST', status='OPEN')\
            .order_by(Item.incident_date.desc(), Item.created_at.desc()).limit(4).all()
        
        recent_found = Item.query.filter_by(item_type='FOUND', status='OPEN')\
            .order_by(Item.incident_date.desc(), Item.created_at.desc()).limit(4).all()

        categories = ItemCategory.query.order_by(ItemCategory.name).all()
    except Exception as e:
        current_app.logger.error(f"Landing page query fallback: {e}")
        stats = {'total_reported': 0, 'total_returned': 0, 'total_users': 0, 'active_listings': 0}
        recent_lost, recent_found, categories = [], [], []

    return render_template('main/index.html',
                           recent_lost=recent_lost,
                           recent_found=recent_found,
                           categories=categories,
                           stats=stats)


@main_bp.route('/about')
def about():
    return render_template('main/about.html')


@main_bp.route('/help')
def help():
    return render_template('main/help.html')


@main_bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html')


@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html')


@main_bp.route('/health')
def health():
    """
    Health check endpoint verifying application availability and database connectivity
    without exposing any passwords, secrets, or internal paths.
    """
    db_ok = False
    status_code = 200
    try:
        # Simple test query to check DB connectivity
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception as e:
        current_app.logger.error(f"Health check DB probe failed: {e}")
        status_code = 503

    return jsonify({
        'status': 'HEALTHY' if db_ok else 'UNHEALTHY',
        'application': 'CampusConnect',
        'version': '1.0.0',
        'database_connected': db_ok
    }), status_code
