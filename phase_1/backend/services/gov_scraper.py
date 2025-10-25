import requests

HF_TOKEN = ""
URL = "https://fatmagician-gov-leads.hf.space/search"

def search_leads(location: str, category: str) -> dict:
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "location": location,
        "category": category
    }

    response = requests.post(URL, json=data, headers=headers)

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {"error": "Non-JSON response", "status_code": response.status_code, "text": response.text}

# if __name__ == "__main__":
#     result = search_leads("los angeles", "barbershop")
#     print(result)
