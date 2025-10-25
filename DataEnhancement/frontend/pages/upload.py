
import streamlit as st
st.set_page_config(page_title="📤 Upload CSV & Normalize", layout="wide")
from streamlit_cookies_controller import CookieController
import pandas as pd
import requests
import jwt

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style/custom_theme.css")
JWT_SECRET = "fallback_secret_change_me_in_production"
JWT_ALGORITHM = "HS256"
BACKEND_URL = "http://localhost:5000"

cookies = CookieController()
token = cookies.get("auth_token")

if token and "logged_in" not in st.session_state:
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        st.session_state.token = token
        st.session_state.logged_in = True
        st.session_state.username = decoded.get("username")
    except jwt.ExpiredSignatureError:
        cookies.delete("auth_token")
        st.warning("Session expired.")
        st.stop()
    except jwt.InvalidTokenError:
        cookies.delete("auth_token")
        st.warning("Invalid session.")
        st.stop()

if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

def auth_headers():
    token = st.session_state.get("token")
    if not token:
        st.error("Missing token. Please log in again.")
        st.stop()
    return {"Authorization": f"Bearer {token}"}

def normalize_name(name):
    return name.strip().lower().replace(" ", "").replace("-", "").replace(".", "") if name else ""

def generate_linkedin_lookup(response_json):
    return {
        normalize_name(r.get("Business Name")): r
        for r in response_json
        if isinstance(r, dict) and r.get("Business Name")
    }

def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])

from streamlit_elements import elements, mui, html
from st_aggrid import AgGrid

st.markdown("""
    <div style='max-width: 800px; margin: 2rem auto; background: fff; border-radius: 1.5rem; box-shadow: 0 2px 12px rgba(24,49,83,0.08); padding: 2.5rem 2rem;'>
        <h1 style='color:183153; font-weight:800; font-size:2rem; margin-bottom:1rem;'>📤 Upload & Normalize Lead Data</h1>
        <div style='color:1e656d; margin-bottom:1.5rem; font-weight:600;'>Upload your leads CSV, normalize columns, select rows, and enrich with Apollo, LinkedIn, and Growjo data!</div>
    </div>
""", unsafe_allow_html=True)

if "normalized_df" not in st.session_state:
    st.session_state.normalized_df = None
if "confirmed_selection_df" not in st.session_state:
    st.session_state.confirmed_selection_df = None

STANDARD_COLUMNS = [
    'Company', 'City', 'State', 'First Name', 'Last Name', 'Email', 'Title', 'Website',
    'LinkedIn URL', 'Industry ', 'Revenue', 'Product/Service Category',
    'Business Type (B2B, B2B2C) ', 'Associated Members', 'Employees range', 'Rev Source', 'Year Founded',
    "Owner's LinkedIn", 'Owner Age', 'Phone Number', 'Additional Notes', 'Score',
    'Email customization 1', 'Subject Line 1', 'Email Customization 2', 'Subject Line 2',
    'LinkedIn Customization 1', 'LinkedIn Customization 2', 'Reasoning for r//y/g'
]

st.markdown(" 📎 Step 1: Upload Your CSV")
uploaded_file = st.file_uploader("Choose a CSV file to upload", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.markdown("<span style='color:1e656d; font-weight:700; font-size:1.05rem;'>✅ File uploaded successfully!</span>", unsafe_allow_html=True)

        st.markdown(" ✅ Step 2: Select Rows to Enhance")
        df['Select Row'] = False
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="editable_df", disabled=df.columns[:-1].tolist())
        selected_df = pd.DataFrame(edited_df)
        rows_to_enhance = selected_df[selected_df['Select Row'] == True].drop(columns=['Select Row'])

        selected_count = len(rows_to_enhance)
        st.markdown(f"**🧮 Selected Rows: `{selected_count}` / 10**")

        if selected_count > 10:
            st.markdown("<span style='color:d7263d; font-weight:700; font-size:1.05rem;'>❌ You can only select up to 10 rows for enhancement.</span>", unsafe_allow_html=True)
            st.button("✅ Confirm Selected Rows", disabled=True)
        else:
            if st.button("✅ Confirm Selected Rows"):
                if selected_count > 0:
                    st.session_state.confirmed_selection_df = rows_to_enhance.copy()
                    st.markdown(f"<span style='color:1e656d; font-weight:700; font-size:1.05rem;'>✅ {selected_count} rows confirmed for normalization and enrichment.</span>", unsafe_allow_html=True)
                else:
                    st.session_state.confirmed_selection_df = df.copy()
                    st.markdown("<span style='color:183153; font-weight:700; font-size:1.05rem;'>ℹ️ No rows selected. Defaulting to all rows.</span>", unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"<span style='color:d7263d; font-weight:700; font-size:1.05rem;'>❌ Failed to process file: {e}</span>", unsafe_allow_html=True)

if st.session_state.confirmed_selection_df is not None:
    data_for_mapping = st.session_state.confirmed_selection_df.copy()

    st.markdown(" 🛠 Step 3: Map Your Columns")
    auto_mapping = {col: col for col in STANDARD_COLUMNS if col in data_for_mapping.columns}
    column_mapping = {}

    st.markdown(" 🔗 Map your CSV columns to our standard format:")
    for target in STANDARD_COLUMNS:
        st.markdown(f"<div style='margin-bottom: -0.5rem; margin-top: 1rem; font-weight: 600;'>{target}</div>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        with col1:
            st.text("From your file")
        with col2:
            default = auto_mapping.get(target, "-- None --")
            selected = st.selectbox(" ", ["-- None --"] + list(data_for_mapping.columns), index=(["-- None --"] + list(data_for_mapping.columns)).index(default) if default != "-- None --" else 0, key=target, label_visibility="collapsed")
        column_mapping[target] = selected if selected != "-- None --" else None

    if st.button("🔄 Normalize CSV"):
        normalized_df = pd.DataFrame()
        for col in STANDARD_COLUMNS:
            if column_mapping[col] and column_mapping[col] in data_for_mapping.columns:
                normalized_df[col] = data_for_mapping[column_mapping[col]]
            else:
                normalized_df[col] = ""

        mapped_input_columns = set(column_mapping.values())
        extra_columns = [col for col in data_for_mapping.columns if col not in mapped_input_columns and col != "Select Row"]
        for col in extra_columns:
            normalized_df[col] = data_for_mapping[col]

        st.session_state.normalized_df = normalized_df.copy()
        st.markdown(" ✅ Normalized Data Preview")
        st.dataframe(normalized_df.head(), use_container_width=True)

        st.download_button("📥 Download Normalized CSV", data=normalized_df.to_csv(index=False).encode("utf-8"), file_name="normalized_leads.csv", mime="text/csv")

if st.session_state.normalized_df is not None and st.session_state.confirmed_selection_df is not None:
    if st.button("🚀 Enhance with Apollo, LinkedIn, and Growjo Data"):
        st.markdown("⏳ Please wait while we enrich company data...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        base_df = st.session_state.normalized_df.copy()
        confirmed_df = st.session_state.confirmed_selection_df.copy()
        enhanced_df = base_df.copy()

        mask = base_df["Company"].isin(confirmed_df["Company"])
        rows_to_update = enhanced_df[mask].copy()

        apollo_domains = rows_to_update["Company"].dropna().unique().tolist()
        apollo_response = requests.post(f"{BACKEND_URL}/api/apollo-info", json=[{"domain": d} for d in apollo_domains], headers=auth_headers())
        apollo_lookup = {r["domain"]: r for r in apollo_response.json() if "domain" in r}

        linkedin_payload = [
            {
                "company": str(row.get("Company", "")),
                "city": str(row.get("City", "")),
                "state": str(row.get("State", "")),
                "website": str(row.get("Website", ""))
            }
            for _, row in rows_to_update.iterrows()
        ]
        linkedin_response = requests.post(f"{BACKEND_URL}/api/linkedin-info-batch", json=linkedin_payload, headers=auth_headers())
        linkedin_lookup = generate_linkedin_lookup(linkedin_response.json())

        for i, (idx, row) in enumerate(rows_to_update.iterrows()):
            domain = row["Company"]
            apollo = apollo_lookup.get(domain, {})
            linkedin = linkedin_lookup.get(normalize_name(domain), {})

            revenue = apollo.get("annual_revenue_printed", "")
            if not revenue:
                try:
                    growjo_response = requests.get(f"{BACKEND_URL}/api/get-revenue", params={"company": domain}, headers=auth_headers())
                    if growjo_response.status_code == 200:
                        revenue = growjo_response.json().get("estimated_revenue", "")
                except:
                    revenue = ""

            if not str(row["Revenue"]).strip():
                rows_to_update.at[idx, "Revenue"] = revenue
            if not str(row["Year Founded"]).strip():
                rows_to_update.at[idx, "Year Founded"] = apollo.get("founded_year", "") or linkedin.get("Founded", "")
            if not str(row["Website"]).strip():
                rows_to_update.at[idx, "Website"] = apollo.get("website_url", "")
            if not str(row["LinkedIn URL"]).strip():
                rows_to_update.at[idx, "LinkedIn URL"] = apollo.get("linkedin_url", "") or linkedin.get("LinkedIn Link", "")
            if not str(row["Industry "]).strip():
                rows_to_update.at[idx, "Industry "] = linkedin.get("Industry", "")
            if not str(row["Associated Members"]).strip():
                rows_to_update.at[idx, "Associated Members"] = linkedin.get("Associated Members", "")
            if not str(row["Employees range"]).strip():
                rows_to_update.at[idx, "Employees range"] = linkedin.get("Employees", "")
            if not str(row["Product/Service Category"]).strip():
                rows_to_update.at[idx, "Product/Service Category"] = linkedin.get("Specialties", "")

             === Growjo Contact Info Integration ===
            growjo_res = requests.post(f"{BACKEND_URL}/api/growjo", json={"company": domain, "headless": True}, headers=auth_headers())
            if growjo_res.status_code == 200:
                people = growjo_res.json()
                if people:
                    person = people[0]
                    first, last = split_name(person.get("name", ""))
                    contact = person.get("contact_info", "")
                    email = ""
                    phone = ""
                    for line in contact.split("\n"):
                        if "email" in line.lower():
                            email = line.split(":")[-1].strip()
                        if "phone" in line.lower():
                            phone = line.split(":")[-1].strip()
                    if not str(row["First Name"]).strip():
                        rows_to_update.at[idx, "First Name"] = first
                    if not str(row["Last Name"]).strip():
                        rows_to_update.at[idx, "Last Name"] = last
                    if not str(row["Email"]).strip():
                        rows_to_update.at[idx, "Email"] = email
                    if not str(row["Phone Number"]).strip():
                        rows_to_update.at[idx, "Phone Number"] = phone
                    if not str(row["Owner's LinkedIn"]).strip():
                        rows_to_update.at[idx, "Owner's LinkedIn"] = person.get("linkedin", "")
                    if not str(row["Title"]).strip():
                        rows_to_update.at[idx, "Title"] = person.get("title", "")

            progress_bar.progress((i + 1) / len(rows_to_update))
            status_text.text(f"Enhanced {i + 1} of {len(rows_to_update)} rows")

        enhanced_df.update(rows_to_update)

        st.success("✅ Enrichment complete!")
        st.dataframe(enhanced_df.head(), use_container_width=True)
        csv = enhanced_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Enhanced CSV", csv, file_name="apollo_linkedin_growjo_enriched.csv", mime="text/csv")
