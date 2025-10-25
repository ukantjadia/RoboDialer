def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])


def normalize_website(website):
    if not website:
        return ""

    # Import urlparse inside the function to avoid circular imports
    from urllib.parse import urlparse

    # First perform basic cleaning
    website = website.strip().lower()

    # Add protocol if missing to make urlparse work properly
    if not website.startswith(("http://", "https://")):
        website = "http://" + website

    # Use urlparse to extract just the domain (netloc)
    parsed = urlparse(website)
    domain = parsed.netloc

    # Remove www. prefix
    domain = domain.replace("www.", "")

    return domain


# Simulated data (same as in real test)
growjo = {
    "company_name": "zoom",
    "company_website": "https://zoom.us/",
    "decider_email": "eric.yuan@zoom.us",
    "decider_linkedin": "not found",
    "decider_name": "Eric Yuan",
    "decider_phone": "not found",
    "decider_title": "Founder & CEO",
    "employee_count": "11168",
    "industry": "Event Tech",
    "input_name": "zoom",
    "interests": "saas",
    "location": "San Francisco, CA",
    "revenue": "$3.9B",
}

apollo = {
    "domain": "zoom.us",
    "founded_year": "2013",
    "linkedin_url": "http://www.linkedin.com/company/zoom",
    "keywords": "video conferencing, online meetings",
    "annual_revenue_printed": "4.5B",
    "website_url": "http://www.zoom.com",
    "employee_count": "12000",
}

apollo_person = {
    "domain": "zoom.us",
    "company": "Zoom",
    "first_name": "Eric",
    "last_name": "Yuan",
    "title": "Founder & CEO",
    "email": "eric.yuan@zoom.us",
    "phone_number": "+18887999666",
    "linkedin_url": "http://www.linkedin.com/in/ericsyuan",
}

# === Simulated Upload Logic ===
def test_fallback_merge(growjo, apollo, apollo_person):
    row = {
        "Company": "",
        "City": "SomeCityBefore",
        "State": "OldState",
        "Website": "",
        "Revenue": "",
        "Rev Source": "",
        "Employees count": "",
        "Industry ": "",
        "Product/Service Category": "",
        "Email": "",
        "Phone Number": "",
        "Owner's LinkedIn": "",
        "Title": "",
        "First Name": "",
        "Last Name": "",
        "LinkedIn URL": "",
    }

    def val(v):
        return v and v.lower() != "not found"

    def fill(col, val1, val2):
        if not str(row.get(col, "")).strip():
            row[col] = val1 or val2 or ""

    row["Company"] = growjo.get("company_name", row["Company"])

    if growjo.get("location"):
        parts = growjo["location"].split(", ")
        if len(parts) > 0:
            row["City"] = parts[0]
        if len(parts) > 1:
            row["State"] = parts[1]

    fill("Revenue", growjo.get("revenue"), apollo.get("annual_revenue_printed"))
    row["Rev Source"] = "Growjo" if val(growjo.get("revenue")) else "Apollo"

    fill("Website", growjo.get("company_website"), apollo.get("website_url"))
    fill("LinkedIn URL", growjo.get("decider_linkedin"), apollo.get("linkedin_url"))
    fill("Industry ", growjo.get("industry"), apollo.get("keywords"))
    fill("Associated Members", "", "")
    fill("Employees count", growjo.get("employee_count"), apollo.get("employee_count"))
    fill("Product/Service Category", growjo.get("interests"), apollo.get("keywords"))

    # Decision maker scoring
    growjo_fields = [
        growjo.get("decider_name", ""),
        growjo.get("decider_email", ""),
        growjo.get("decider_phone", ""),
        growjo.get("decider_linkedin", ""),
        growjo.get("decider_title", ""),
    ]
    apollo_fields = [
        f"{apollo_person.get('first_name', '')} {apollo_person.get('last_name', '')}".strip(),
        apollo_person.get("email", ""),
        apollo_person.get("phone_number", ""),
        apollo_person.get("linkedin_url", ""),
        apollo_person.get("title", ""),
    ]
    growjo_score = sum(1 for f in growjo_fields if val(f))
    apollo_score = sum(1 for f in apollo_fields if val(f))
    use_apollo = apollo_score > growjo_score

    if use_apollo:
        fill("Email", apollo_person.get("email"), "")
        fill("Phone Number", apollo_person.get("phone_number"), "")
        fill("Owner's LinkedIn", apollo_person.get("linkedin_url"), "")
        fill("Title", apollo_person.get("title"), "")
        fill("First Name", apollo_person.get("first_name"), "")
        fill("Last Name", apollo_person.get("last_name"), "")
    else:
        decider_name = growjo.get("decider_name", "")
        first_name, last_name = split_name(decider_name)
        fill("Email", growjo.get("decider_email"), "")
        fill("Phone Number", growjo.get("decider_phone"), "")
        fill("Owner's LinkedIn", growjo.get("decider_linkedin"), "")
        fill("Title", growjo.get("decider_title"), "")
        fill("First Name", first_name, "")
        fill("Last Name", last_name, "")

    return row


# === Run
final_result = test_fallback_merge(growjo, apollo, apollo_person)

print("=== Final Enrichment Result ===")
for k, v in final_result.items():
    print(f"{k:<25}: {v}")
