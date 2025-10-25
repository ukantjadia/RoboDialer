import requests

BACKEND_URL = "http://localhost:5050"
ENDPOINT = "/api/apollo-scrape-batch"

# Replace or extend this list as needed
domains = ["lumious.com"]

response = requests.post(
    f"{BACKEND_URL}{ENDPOINT}",
    json={"domains": domains},
    headers={"Content-Type": "application/json"},  # Add auth if needed
)

if response.status_code == 200:
    results = response.json()
    print("=== Apollo Company Result ===")
    for r in results:
        print(f"Domain              : {r.get('domain')}")
        print(f"Founded Year        : {r.get('founded_year')}")
        print(f"LinkedIn URL        : {r.get('linkedin_url')}")
        print(f"Keywords            : {r.get('keywords')}")
        print(f"Industry            : {r.get('industry')}")
        print(f"Annual Revenue      : {r.get('annual_revenue_printed')}")
        print(f"Website URL         : {r.get('website_url')}")
        print(f"Employee Count      : {r.get('employee_count')}")
        print(f"Business Type       : {r.get('business_type')}")
        print("-" * 40)
else:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)
