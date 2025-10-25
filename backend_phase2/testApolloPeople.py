import requests

BACKEND_URL = "http://localhost:5050"
ENDPOINT = "/api/find-best-person-batch"

# Replace or extend this list as needed
domains = ["slack"]

response = requests.post(
    f"{BACKEND_URL}{ENDPOINT}",
    json={"domains": domains},
    headers={"Content-Type": "application/json"},  # Add auth if needed
)

if response.status_code == 200:
    results = response.json()
    print("=== Apollo People Result ===")
    for r in results:
        print(f"Domain       : {r.get('domain')}")
        print(f"Company      : {r.get('company')}")
        print(f"First Name   : {r.get('first_name')}")
        print(f"Last Name    : {r.get('last_name')}")
        print(f"Title        : {r.get('title')}")
        print(f"Email        : {r.get('email')}")
        print(f"Phone Number : {r.get('phone_number')}")
        print(f"LinkedIn URL : {r.get('linkedin_url')}")
        print("-" * 40)
else:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)
