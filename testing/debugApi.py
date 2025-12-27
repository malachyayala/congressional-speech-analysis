import requests

API_KEY = "RgWUXBtZYgRdRoGg8h4fwdjBfekYbsPhCCbMl9sC"
# Let's test a known active date: Jan 2012
url = "https://api.govinfo.gov/collections/CREC/2012-01-01T00:00:00Z"
params = {"api_key": API_KEY, "pageSize": 10, "offsetMark": "*"}

resp = requests.get(url, params=params)
print(f"Status: {resp.status_code}")
data = resp.json()
pkgs = data.get('packages', [])
print(f"Found {len(pkgs)} packages.")
if pkgs:
    print(f"First Package ID: {pkgs[0]['packageId']}")
else:
    print("API returned NO packages for this date.")