import os
import io
import pytest
from app import create_app
from app.extensions import db
from app.seed import seed_database

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'instance', 'campusconnect_test.db')


@pytest.fixture(scope='session')
def app():
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def reset_database(app):
    """Ensure every test runs against a clean, newly seeded database state."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        seed_database()
        db.session.commit()
        yield
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client):
    """Helper to log in as specific user and return the response."""
    def _login(email, password):
        client.get('/auth/logout')
        return client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)
    return _login


@pytest.fixture
def sample_image():
    """Generates a tiny valid 1x1 PNG in memory for upload testing."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new('RGB', (10, 10), color='blue')
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
