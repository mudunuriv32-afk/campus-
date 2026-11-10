import os
import threading
import time
import pytest
from werkzeug.serving import make_server
from app import create_app
from app.extensions import db
from app.seed import seed_database


class ServerThread(threading.Thread):
    def __init__(self, app, port=5055):
        super().__init__(daemon=True)
        self.server = make_server('127.0.0.1', port, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope='session')
def live_server():
    """Run real live Flask server for browser Playwright tests."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        seed_database()

    server = ServerThread(app, port=5055)
    server.start()
    time.sleep(1)  # Allow server to bind and start listening
    
    yield "http://127.0.0.1:5055"

    server.shutdown()
