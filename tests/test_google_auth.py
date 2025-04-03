import pytest
from unittest.mock import patch, MagicMock
from main import app, Users, db
from flask import session

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_google_login_route(client):
    """Test that the Google login route redirects to Google"""
    response = client.get('/google/login')
    assert response.status_code == 302  # Should be a redirect
    assert 'accounts.google.com' in response.location  # Should redirect to Google

@patch('main.google.authorize_access_token')
@patch('main.google.parse_id_token')
def test_google_callback_new_user(mock_parse_id_token, mock_auth_token, client):
    """Test Google callback with a new user"""
    # Mock the Google token response
    mock_auth_token.return_value = {'token': 'dummy_token'}
    
    # Mock the user info that Google would return
    mock_parse_id_token.return_value = {
        'email': 'test@example.com',
        'name': 'Test User'
    }
    
    with client.session_transaction() as sess:
        sess['nonce'] = 'test_nonce'
    
    response = client.get('/callback')
    
    # Should redirect to settings page after successful login
    assert response.status_code == 302
    assert '/settings' in response.location
    
    # Verify user was created in database
    with app.app_context():
        user = Users.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.name == 'Test User'

@patch('main.google.authorize_access_token')
@patch('main.google.parse_id_token')
def test_google_callback_existing_user(mock_parse_id_token, mock_auth_token, client):
    """Test Google callback with an existing user"""
    # Create an existing user
    with app.app_context():
        user = Users(email='test@example.com', name='Test User')
        db.session.add(user)
        db.session.commit()
    
    # Mock the Google token response
    mock_auth_token.return_value = {'token': 'dummy_token'}
    
    # Mock the user info that Google would return
    mock_parse_id_token.return_value = {
        'email': 'test@example.com',
        'name': 'Test User'
    }
    
    with client.session_transaction() as sess:
        sess['nonce'] = 'test_nonce'
    
    response = client.get('/callback')
    
    # Should redirect to settings page after successful login
    assert response.status_code == 302
    assert '/settings' in response.location

@patch('main.google.authorize_access_token')
def test_google_callback_error(mock_auth_token, client):
    """Test Google callback with an error"""
    # Mock an error in the Google token response
    mock_auth_token.side_effect = Exception('Token error')
    
    with client.session_transaction() as sess:
        sess['nonce'] = 'test_nonce'
    
    response = client.get('/callback')
    
    # Should redirect to error page
    assert response.status_code == 200
    assert b'error_page' in response.data 