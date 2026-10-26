
from unittest.mock import patch


def test_search_barcode_form_submission(client, post):
    with patch('main.get_product_info', return_value={'product': {'product_name': 'Test food'}}), \
         patch('main.get_specific_ingredient', return_value=(True, ['Salt'])), \
         patch('main.get_ingredient', return_value={'name': 'Salt', 'description': 'A seasoning', 'rating': 'neutral'}):
        response = post('/', data={'barcode': '013000626095'})
    assert response.status_code == 200
    assert b'Test food' in response.data
    assert b'A seasoning' in response.data
