import pandas as pd

# Simulated API response from Growjo
api_response = {
    "company_name": "Dermatologist Medical Group of North County inc",
    "company_website": "https://dmgnc.com/",
    "decider_email": "heidisuitor@dmgnc.com",
    "decider_linkedin": "https://www.linkedin.com/in/heidisuitor",
    "decider_name": "Heidi Suitor",
    "decider_phone": "2197757136",
    "decider_title": "Operations Manager",
    "employee_count": "39",
    "industry": "Medical Offices",
    "input_name": "Dermatologist Medical Group of North County inc",
    "interests": "N/A",
    "location": "San Diego, CA",
    "revenue": "$6.9M",
}

# Columns from your Streamlit UI
STANDARD_COLUMNS = [
    "Company",
    "City",
    "State",
    "First Name",
    "Last Name",
    "Email",
    "Title",
    "Website",
    "LinkedIn URL",
    "Industry ",
    "Revenue",
    "Product/Service Category",
    "Business Type (B2B, B2B2C) ",
    "Associated Members",
    "Employees count",
    "Rev Source",
    "Year Founded",
    "Owner's LinkedIn",
    "Owner Age",
    "Phone Number",
    "Additional Notes",
    "Score",
    "Email customization #1",
    "Subject Line #1",
    "Email Customization #2",
    "Subject Line #2",
    "LinkedIn Customization #1",
    "LinkedIn Customization #2",
    "Reasoning for r//y/g",
]

# Create a blank row
row = {col: "" for col in STANDARD_COLUMNS}

# Fill values using Growjo-style API keys
row["Company"] = api_response.get("company_name")
if api_response.get("location"):
    parts = api_response["location"].split(", ")
    row["City"] = parts[0] if len(parts) > 0 else ""
    row["State"] = parts[1] if len(parts) > 1 else ""

row["Email"] = api_response.get("decider_email")
row["Title"] = api_response.get("decider_title")
row["Website"] = api_response.get("company_website")
row["LinkedIn URL"] = api_response.get("decider_linkedin")
row["Industry "] = api_response.get("industry")
row["Revenue"] = api_response.get("revenue")
row["Employees count"] = api_response.get("employee_count")
row["Phone Number"] = api_response.get("decider_phone")

# Split name
def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])


first_name, last_name = split_name(api_response.get("decider_name", ""))
row["First Name"] = first_name
row["Last Name"] = last_name

# Output as a DataFrame
df = pd.DataFrame([row])
print(
    df[
        [
            "Company",
            "City",
            "State",
            "First Name",
            "Last Name",
            "Email",
            "Title",
            "Website",
            "LinkedIn URL",
            "Industry ",
            "Revenue",
            "Employees count",
            "Phone Number",
        ]
    ]
)
