import requests
import time
import datetime

# --- CONFIGURATION ---
API_KEY = "RgWUXBtZYgRdRoGg8h4fwdjBfekYbsPhCCbMl9sC"  # Paste your key here

def check_govinfo_limit(key):
    print("\n--- CHECKING GOVINFO API ---")
    url = "https://api.govinfo.gov/collections"
    
    try:
        response = requests.get(url, params={'api_key': key, 'pageSize': 1})
        
        if response.status_code == 200:
            headers = response.headers
            print(f"Status: ✅ Active")
            print(f"Limit per Hour:     {headers.get('X-RateLimit-Limit', 'Unknown')}")
            print(f"Requests Remaining: {headers.get('X-RateLimit-Remaining', 'Unknown')}")
            
            # Calculate reset time
            reset_ts = headers.get('X-RateLimit-Reset') # often in epoch seconds
            if reset_ts:
                # Sometimes it is seconds remaining, sometimes a timestamp. 
                # GovInfo usually uses a timestamp.
                try:
                    reset_time = datetime.datetime.fromtimestamp(int(reset_ts))
                    print(f"Limit Resets At:    {reset_time.strftime('%I:%M:%S %p')}")
                except:
                    print(f"Limit Resets In:    {reset_ts} seconds")
        else:
            print(f"Status: ❌ Error {response.status_code}")
            print(f"Message: {response.text}")
            
    except Exception as e:
        print(f"Connection Failed: {e}")

def check_congress_limit(key):
    print("\n--- CHECKING CONGRESS.GOV API ---")
    url = "https://api.congress.gov/v3/bill"
    
    try:
        response = requests.get(url, params={'api_key': key, 'limit': 1, 'format': 'json'})
        
        if response.status_code == 200:
            headers = response.headers
            print(f"Status: ✅ Active")
            # Congress.gov headers might differ slightly
            print(f"Limit per Hour:     {headers.get('X-RateLimit-Limit', 'Unknown')}")
            print(f"Requests Remaining: {headers.get('X-RateLimit-Remaining', 'Unknown')}")
        else:
            print(f"Status: ❌ Error {response.status_code}")
            print(f"Message: {response.text}")

    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    if API_KEY == "YOUR_API_KEY_HERE":
        print("Please edit the script and paste your API_KEY first!")
    else:
        check_govinfo_limit(API_KEY)
        check_congress_limit(API_KEY)
        print("\n-------------------------------------------")
        print("NOTE: 'Requests Remaining' is usually a rolling 1-hour window.")