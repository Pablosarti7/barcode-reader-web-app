import requests
import os
from utils.utils import split_string_advanced

def get_all_products():
    url = "https://food-products-api-production-8b0b.up.railway.app/all-products"

    try:
        # Perform the GET request
        response = requests.get(url)
        
        # Raise an error for bad status codes
        response.raise_for_status()  # This will raise an HTTPError for non-200 responses
        
        # Attempt to parse the response JSON
        data = response.json()
        
        return data
    
    # Handle connection errors (network issues, etc.)
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to the server. Please check your network."}

    # Handle timeout errors
    except requests.exceptions.Timeout:
        return {"error": "The request timed out. Please try again later."}

    # Handle non-200 status codes
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}

    # Handle any other requests-related errors
    except requests.exceptions.RequestException as req_err:
        return {"error": f"An error occurred while making the request: {req_err}"}

    # Handle invalid JSON in the response
    except ValueError:
        return {"error": "Invalid response format. Unable to parse JSON."}


PRODUCTS_API_KEY = os.environ.get('PRODUCTS_API_KEY')

def add_product(products):
    add_url = 'https://food-products-api-production-8b0b.up.railway.app/add-product'
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": PRODUCTS_API_KEY
    }
    
    try:
        # Perform the POST request
        response = requests.post(add_url, headers=headers, data=products)
        
        # Raise an error for bad status codes
        response.raise_for_status()  # Will raise HTTPError for non-200 status codes
        
        # Handle successful response
        if response.status_code == 201:
            return "Product added successfully"
        
        # Handle specific 400 Bad Request status
        elif response.status_code == 400:
            return "Invalid product data"
        
        # Handle any other non-successful response (though raise_for_status handles most)
        else:
            return "An unexpected error occurred"

    # Handle connection errors
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to the server. Please check your network."}

    # Handle timeout errors
    except requests.exceptions.Timeout:
        return {"error": "The request timed out. Please try again later."}

    # Handle non-200 HTTP responses (e.g., 4xx or 5xx errors)
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}

    # Handle any other requests-related errors
    except requests.exceptions.RequestException as req_err:
        return {"error": f"An error occurred while making the request: {req_err}"}


# New function to get a specific ingredient
def get_specific_ingredient(product_name):
    ingredient_url = f"https://food-products-api-production-8b0b.up.railway.app/product/{product_name}"

    try:
        # Perform the GET request
        response = requests.get(ingredient_url)
        
        # Raise an error for bad status codes
        response.raise_for_status()  # This will raise an HTTPError for non-200 responses

        # Attempt to parse the response JSON
        data = response.json()
        
        string_from_data = data['ingredients']
        list_of_ingredients = split_string_advanced(string_from_data)
        
        return True, list_of_ingredients
    
    # Handle connection errors
    except requests.exceptions.ConnectionError:
        return False, {"error": "Failed to connect to the server. Please check your network."}

    # Handle timeout errors
    except requests.exceptions.Timeout:
        return False, {"error": "The request timed out. Please try again later."}

    # Handle non-200 status codes
    except requests.exceptions.HTTPError as http_err:
        return False, {"error": f"HTTP error occurred: {http_err}"}

    # Handle any other requests-related errors
    except requests.exceptions.RequestException as req_err:
        return False, {"error": f"An error occurred while making the request: {req_err}"}

    # Handle invalid JSON in the response
    except ValueError:
        return False, {"error": "Invalid response format. Unable to parse JSON."}

