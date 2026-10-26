from unittest.mock import patch

@patch('main.get_ingredient', return_value={'name': 'Salt', 'description': 'A seasoning', 'rating': 'neutral'})
def test_search_ingredient_form_submission(lookup, client, post):
    """Test the search ingredient form submission and response"""
    # Verify a valid submission actually queries and displays the ingredient.
    response = post('/search', data={
        'ingredient': 'salt',  # The form field name from SearchIngredient form
    }, follow_redirects=True)
    
    # Check if the request was successful
    assert response.status_code == 200
    lookup.assert_called_once_with('salt')
    assert b'A seasoning' in response.data

def test_search_ingredient_form_empty(client, post):
    """Test the search ingredient form with empty input"""
    response = post('/search', data={
        'ingredient': '',
    }, follow_redirects=True)
    
    # Should still return 200 but with empty results
    assert response.status_code == 200
    assert b'Your ingredient information will appear here' in response.data

def test_search_ingredient_get_request(client):
    """Test accessing the search page with GET request"""
    response = client.get('/search')
    assert response.status_code == 200
    assert b'Search specific ingredients' in response.data