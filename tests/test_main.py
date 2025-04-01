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