import requests
import json
import os

RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY", "8efdc915106b4bce818b259f9af58484")

url = "https://api.rentcast.io/v1/properties"
headers = {
    "Accept": "application/json",
    "X-Api-Key": RENTCAST_API_KEY
}
params = {
    "address": "13389 Arbor Pointe Cir, Apt 204, Tampa, FL 33617"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    if len(data) > 0:
        print("Fields available in /properties response:")
        print(json.dumps(data[0], indent=2))
    else:
        print("No listings found")
else:
    print(f"Error {response.status_code}: {response.text}")
