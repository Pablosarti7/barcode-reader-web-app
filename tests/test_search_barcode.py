import pytest
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_search_barcode_form_submission(client):
    """Test the search barcode form submission and response"""
    # Make a POST request to the home endpoint with test data
    response = client.post('/', data={
        'barcode': '013000626095',  # Example barcode
        'csrf_token': 'dummy',  # Required for form validation
    }, follow_redirects=True)
    
    # Check if the request was successful
    assert response.status_code == 200
