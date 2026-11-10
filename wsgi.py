import os
from app import create_app
from app.extensions import db

app = create_app(os.getenv('FLASK_CONFIG', os.getenv('FLASK_ENV', 'development')))

# Automatically initialize database schema and seed data on startup
if os.getenv('AUTO_INIT_DB', 'true').lower() in ('1', 'true', 'yes'):
    with app.app_context():
        try:
            db.create_all()
            from app.seed import seed_database
            seed_database()
            app.logger.info("Database schema and seed data verified.")
        except Exception as e:
            app.logger.warning(f"Startup DB auto-init note: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

