import requests

def get_all_products():
    url = "https://food-products-api-production.up.railway.app/all-products"

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


    

def add_product(products):
    add_url = 'https://food-products-api-production.up.railway.app/add-product'
    headers = {
        "Content-Type": "application/json"
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
