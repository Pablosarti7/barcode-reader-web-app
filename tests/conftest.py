"""Tests never use a developer's database, .env credentials, or external services."""
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['APP_ENV'] = 'development'
os.environ['SECRET_KEY'] = 'test-only-session-secret'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from main import app, db  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_app(monkeypatch):
    import requests
    import httpx
    monkeypatch.setattr(requests.sessions.Session, 'request',
                        Mock(side_effect=AssertionError('Mock external HTTP requests in tests')))
    monkeypatch.setattr(httpx.Client, 'send',
                        Mock(side_effect=AssertionError('Mock external HTTP requests in tests')))
    monkeypatch.setitem(app.config, 'TESTING', True)
    monkeypatch.setitem(app.config, 'WTF_CSRF_ENABLED', True)
    monkeypatch.setitem(app.config, 'GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setitem(app.config, 'GOOGLE_CLIENT_SECRET', 'test-secret')
    monkeypatch.setitem(app.config, 'STRIPE_WEBHOOK_SECRET', 'test-webhook-secret')
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def post(client):
    """Submit browser forms with a real CSRF token from the same session."""
    import re
    def submit(path, data=None, **kwargs):
        page = client.get('/')
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data).group(1).decode()
        return client.post(path, data={**(data or {}), 'csrf_token': token}, **kwargs)
    return submit
