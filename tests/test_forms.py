import pytest
from main import app
from forms.forms import SearchIngredient

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_search_ingredient_form_submission(client):
    """Test the search ingredient form submission and response"""
    # Make a POST request to the search endpoint with test data
    response = client.post('/search', data={
        'ingredient': 'salt',  # The form field name from SearchIngredient form
        'csrf_token': 'dummy',  # Required for form validation
    }, follow_redirects=True)
    
    # Check if the request was successful
    assert response.status_code == 200

def test_search_ingredient_form_empty(client):
    """Test the search ingredient form with empty input"""
    response = client.post('/search', data={
        'ingredient': '',
        'csrf_token': 'dummy',
    }, follow_redirects=True)
    
    # Should still return 200 but with empty results
    assert response.status_code == 200
    assert b'Your ingredient information will appear here' in response.data

def test_search_ingredient_get_request(client):
    """Test accessing the search page with GET request"""
    response = client.get('/search')
    assert response.status_code == 200
    assert b'Search specific ingredients' in response.data