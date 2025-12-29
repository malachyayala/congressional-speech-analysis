import requests
import json

# 1. Configuration
# You can get an API key here: https://api.data.gov/signup/
API_KEY = 'RgWUXBtZYgRdRoGg8h4fwdjBfekYbsPhCCbMl9sC' 
BASE_URL = 'https://api.govinfo.gov'

def get_all_collections():
    """
    Retrieves a list of all collections available on GovInfo.
    Endpoint: GET /collections
    """
    endpoint = f"{BASE_URL}/collections"
    
    # The API key can typically be passed as a query parameter or header.
    # Using header is often cleaner.
    headers = {
        'X-Api-Key': API_KEY
    }
    
    # Alternatively, use params={'api_key': API_KEY}
    
    try:
        print(f"Requesting: {endpoint}")
        response = requests.get(endpoint, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # The documentation indicates the response includes collectionCode, 
            # collectionName, package and granule counts.
            collections = data.get('collections', [])
            
            print(f"Successfully retrieved {len(collections)} collections:\n")
            
            for collection in collections:
                code = collection.get('collectionCode', 'N/A')
                name = collection.get('collectionName', 'N/A')
                print(f"[{code}] {name}")
                
            return collections
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    get_all_collections()