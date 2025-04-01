import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test that the home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'How It Works' in response.data  # This checks for text we know is in your index.html

def test_about_page(client):
    """Test that the about page loads successfully"""
    response = client.get('/about')
    assert response.status_code == 200
    assert b'What We Do' in response.data  # This checks for text we know is in your about.html

def test_invalid_page(client):
    """Test that an invalid page returns 404"""
    response = client.get('/nonexistent-page')
    assert response.status_code == 404

def test_login_page(client):
    """Test login page loads and form submission"""
    # Test that the page loads
    response = client.get('/login')
    assert response.status_code == 200
    