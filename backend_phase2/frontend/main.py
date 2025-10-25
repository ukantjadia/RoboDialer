import streamlit as st
import pandas as pd
import requests
import time
import os
from dotenv import load_dotenv
from config import BACKEND_URL
import concurrent.futures
from urllib.parse import urlparse


# # ✅ Simple login check using session state only
# if not st.session_state.get("logged_in"):
#     st.warning("🚫 Please log in first.")
#     st.stop()

# ✅ Dummy auth headers (if backend still expects headers)
def auth_headers():
    return {}  # You can return {"Authorization": "dummy"} if needed by backend


def normalize_name(name):
    return name.strip().lower().replace(" ", "").replace("-", "").replace(".", "") if name else ""


def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])


def normalize_website(website):
    if pd.isna(website) or not isinstance(website, str) or not website.strip():
        return ""

    website = website.strip().lower()

    # Add protocol if missing for proper parsing
    if not website.startswith(("http://", "https://")):
        website = "http://" + website

    # Extract domain using urlparse
    parsed = urlparse(website)
    domain = parsed.netloc or parsed.path  # fallback in case urlparse fails

    # Clean up domain
    domain = domain.replace("www.", "").strip("/")

    return domain


def revenue_to_number(revenue_str):
    """Convert revenue like '500K', '2M', '$1.2B' to a numeric float."""
    if not isinstance(revenue_str, str) or revenue_str.strip() == "":
        return 0
    revenue_str = revenue_str.replace("$", "").replace(",", "").strip().upper()
    try:
        if revenue_str.endswith("B"):
            return float(revenue_str[:-1]) * 1_000_000_000
        elif revenue_str.endswith("M"):
            return float(revenue_str[:-1]) * 1_000_000
        elif revenue_str.endswith("K"):
            return float(revenue_str[:-1]) * 1_000
        else:
            return float(revenue_str)
    except ValueError:
        return 0


st.set_page_config(page_title="📤 Upload CSV & Normalize", layout="wide")
st.title("📤 Upload & Normalize Lead Data")
st.markdown(
    """
Welcome! This tool allows you to upload a CSV file and normalize its structure 
to match our standard format, and enrich it with Apollo, LinkedIn, and Growjo data.
"""
)
st.sidebar.markdown("### ⚠️ Instructions")
st.sidebar.markdown(
    """
1. **Upload your `.csv` file** containing company data.
2. **Choose how many rows** you'd like to enrich.
3. During **column mapping**, ensure your dataset's columns match the required normalized fields, especially **Company** and **Website**, or else it will not enrich your data correctly
4. After enrichment, you can **filter specific rows** before downloading if some outputs aren't satisfactory.

---

### 📝 Notes
- On average, enrichment takes **1–3 minutes per row**.
- Data is sourced from **Growjo** and **Apollo**, but these sources may occasionally provide **incomplete or inaccurate information**, so it is better to still verify critical fields manually.
- Fields are enriched using a **combination of sources**. Some rows may be filled entirely from Growjo, some from Apollo, and others using both.
"""
)

if "normalized_df" not in st.session_state:
    st.session_state.normalized_df = None
if "confirmed_selection_df" not in st.session_state:
    st.session_state.confirmed_selection_df = None

STANDARD_COLUMNS = [
    # 🏢 Company Information
    "Company",
    "Website",
    "Industry ",
    "Product/Service Category",
    "Business Type (B2B, B2B2C)",
    "Employees count",
    "Revenue",
    "Year Founded",
    "City",
    "State",
    "LinkedIn URL",
    # 👤 Primary Contact (Decision Maker)
    "First Name",
    "Last Name",
    "Title",
    "Email",
    "Phone Number",
    "Owner's LinkedIn",
    # 🧩 Engagement Details / Notes
    "Source",
    "Score",
]

st.markdown("### 📎 Step 1: Upload Your CSV")
uploaded_file = st.file_uploader("Choose a CSV file to upload", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [col.strip() for col in df.columns]
        st.success("✅ File uploaded successfully!")

        st.markdown("### ✅ Step 2: Select Rows to Enhance")
        df["Select Row"] = False
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key="editable_df",
            disabled=df.columns[:-1].tolist(),
        )
        selected_df = pd.DataFrame(edited_df)
        rows_to_enhance = selected_df[selected_df["Select Row"] == True].drop(
            columns=["Select Row"]
        )
        selected_count = len(rows_to_enhance)
        st.markdown(f"**🧮 Selected Rows: `{selected_count}` / 100**")

        if selected_count > 100:
            st.error("❌ You can only select up to 100 rows for enhancement.")
            st.button("✅ Confirm Selected Rows", disabled=True)
        else:
            if st.button("✅ Confirm Selected Rows"):
                if selected_count > 0:
                    st.session_state.confirmed_selection_df = rows_to_enhance.copy()
                    st.success(f"{selected_count} rows confirmed for normalization and enrichment.")
                else:
                    st.session_state.confirmed_selection_df = df.copy()
                    st.info("No rows selected. Defaulting to all rows.")

    except Exception as e:
        st.error(f"❌ Failed to process file: {e}")

if st.session_state.confirmed_selection_df is not None:
    data_for_mapping = st.session_state.confirmed_selection_df.copy()

    st.markdown("### 🛠 Step 3: Map Your Columns")
    auto_mapping = {col: col for col in STANDARD_COLUMNS if col in data_for_mapping.columns}
    column_mapping = {}

    st.markdown("#### 🔗 Map your CSV columns to our standard format:")
    for target in STANDARD_COLUMNS:
        st.markdown(
            f"<div style='margin-bottom: -0.5rem; margin-top: 1rem; font-weight: 600;'>{target}</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1, 2])
        with col1:
            st.text("From your file")
        with col2:
            default = auto_mapping.get(target, "-- None --")
            selected = st.selectbox(
                " ",
                ["-- None --"] + list(data_for_mapping.columns),
                index=(["-- None --"] + list(data_for_mapping.columns)).index(default)
                if default != "-- None --"
                else 0,
                key=target,
                label_visibility="collapsed",
            )
        column_mapping[target] = selected if selected != "-- None --" else None

    if st.button("🔄 Normalize CSV"):
        normalized_df = pd.DataFrame()
        for col in STANDARD_COLUMNS:
            if column_mapping[col] and column_mapping[col] in data_for_mapping.columns:
                normalized_df[col] = data_for_mapping[column_mapping[col]]
            else:
                normalized_df[col] = ""

        mapped_input_columns = set(column_mapping.values())
        extra_columns = [
            col
            for col in data_for_mapping.columns
            if col not in mapped_input_columns and col != "Select Row"
        ]
        for col in extra_columns:
            normalized_df[col] = data_for_mapping[col]

        st.session_state.normalized_df = normalized_df.copy()
        st.markdown("### ✅ Normalized Data Preview")
        st.dataframe(normalized_df.head(), use_container_width=True)

        st.download_button(
            "📥 Download Normalized CSV",
            data=normalized_df.to_csv(index=False).encode("utf-8"),
            file_name="normalized_leads.csv",
            mime="text/csv",
        )

if (
    st.session_state.normalized_df is not None
    and st.session_state.confirmed_selection_df is not None
):
    if st.button("🚀 Enrich Data"):
        st.markdown("⏳ Please wait while we enrich company data...")
        start_time = time.time()
        progress_bar = st.progress(0)
        status_text = st.empty()

        base_df = st.session_state.normalized_df.copy()
        enhanced_df = base_df.copy()

        rows_to_update = base_df[base_df["Company"].notnull()].copy()

        # Step 1: Prepare all domains and company names first
        company_names = [row["Company"] for _, row in rows_to_update.iterrows()]
        websites = [
            normalize_website(row.get("Website", "")) for _, row in rows_to_update.iterrows()
        ]

        # First, run Growjo to get websites for companies missing them
        st.markdown("🔍 Fetching missing websites...")
        companies_missing_websites = []
        companies_missing_websites_indices = []

        for i, (idx, row) in enumerate(rows_to_update.iterrows()):
            company = row["Company"]
            website = normalize_website(row.get("Website", ""))
            if not website and company:
                companies_missing_websites.append({"company": company})
                companies_missing_websites_indices.append((i, idx))

        # Only call the Growjo API if there are companies missing websites
        growjo_websites_response = []
        if companies_missing_websites:
            growjo_websites_response = requests.post(
                f"{BACKEND_URL}/api/scrape-growjo-batch",
                json=companies_missing_websites,
                headers=auth_headers(),
            ).json()

        # Update the websites for companies with missing websites
        for i, (list_idx, df_idx) in enumerate(companies_missing_websites_indices):
            if i < len(growjo_websites_response):
                growjo_result = growjo_websites_response[i]
                website = growjo_result.get("company_website", "")
                if website and website.lower() != "not found":
                    rows_to_update.at[df_idx, "Website"] = website
                    st.markdown(
                        f"✅ Found website for {growjo_result.get('company_name')}: {website}"
                    )

        # Refresh websites list with newly found websites
        websites = [
            normalize_website(row.get("Website", "")) for _, row in rows_to_update.iterrows()
        ]
        unique_websites = list(set([w for w in websites if w]))

        # Step 2: Run all 3 APIs in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_growjo = executor.submit(
                requests.post,
                f"{BACKEND_URL}/api/scrape-growjo-batch",
                json=[{"company": c} for c in company_names],
                headers=auth_headers(),
            )
            future_apollo = executor.submit(
                requests.post,
                f"{BACKEND_URL}/api/apollo-scrape-batch",
                json={"domains": unique_websites},
            )
            future_apollo_person = executor.submit(
                requests.post,
                f"{BACKEND_URL}/api/find-best-person-batch",
                json={"domains": unique_websites},
                headers=auth_headers(),
            )

            growjo_response = future_growjo.result().json()
            apollo_response = future_apollo.result().json()
            apollo_person_response = future_apollo_person.result().json()

        # Step 3: Build lookup maps
        growjo_map = {
            (item.get("company_name") or item.get("input_name", "")).lower(): item
            for item in growjo_response
        }
        apollo_map = {item.get("domain"): item for item in apollo_response if item.get("domain")}
        apollo_person_map = {
            item.get("domain"): item for item in apollo_person_response if item.get("domain")
        }

        # Step 4: Merge per row
        for i, (idx, row) in enumerate(rows_to_update.iterrows()):
            company = row["Company"]
            company_lower = company.lower()
            website_norm = normalize_website(row.get("Website", ""))
            growjo = growjo_map.get(company_lower, {})
            apollo = apollo_map.get(website_norm, {})
            apollo_person = apollo_person_map.get(website_norm, {})

            def fill(col, val1, val2):
                # Replace locked Apollo email with 'N/A' before filling
                if col == "Email":
                    if val1 == "email_not_unlocked@domain.com":
                        val1 = "N/A"
                    if val2 == "email_not_unlocked@domain.com":
                        val2 = "N/A"
                if col in row and not str(row[col]).strip():
                    rows_to_update.at[idx, col] = val1 or val2 or ""

            # General fields: Growjo first, fallback to Apollo
            rows_to_update.at[idx, "Company"] = growjo.get("company_name", row["Company"])

            # Always overwrite City/State if Growjo location is present
            if growjo.get("location"):
                parts = growjo["location"].split(", ")
                if len(parts) > 0 and parts[0]:
                    rows_to_update.at[idx, "City"] = parts[0]
                if len(parts) > 1 and parts[1]:
                    rows_to_update.at[idx, "State"] = parts[1]

            # Always overwrite Website if available from either Growjo or Apollo
            if growjo.get("company_website"):
                rows_to_update.at[idx, "Website"] = growjo["company_website"]
            elif apollo.get("company_website"):
                rows_to_update.at[idx, "Website"] = apollo["company_website"]

            fill("Revenue", growjo.get("revenue"), apollo.get("annual_revenue_printed"))
            # rows_to_update.at[idx, "Rev Source"] = "Growjo" if growjo.get("revenue") else "Apollo"

            fill("Year Founded", apollo.get("founded_year"), "")  # ✅ Add this line
            fill("Website", growjo.get("company_website"), apollo.get("company_website"))
            fill("LinkedIn URL", apollo.get("linkedin_url"), "")
            fill("Industry ", growjo.get("industry"), apollo.get("industry"))
            fill("Associated Members", "", "")
            fill("Employees count", growjo.get("employee_count"), apollo.get("employee_count"))
            # ✅ Business Type (B2B, B2C, B2B2C)
            fill("Business Type (B2B, B2B2C)", apollo.get("business_type", ""), "")
            # Apollo may return list of keywords
            apollo_keywords = (
                ", ".join(apollo.get("keywords"))
                if isinstance(apollo.get("keywords"), list)
                else apollo.get("keywords", "")
            )
            growjo_interests = growjo.get("interests", "")

            # Use Apollo if Growjo returns "N/A" or is missing
            if growjo_interests.strip().lower() == "n/a" or not growjo_interests.strip():
                rows_to_update.at[idx, "Product/Service Category"] = apollo_keywords
            else:
                rows_to_update.at[idx, "Product/Service Category"] = growjo_interests

            # Decision-maker: Compare Growjo vs ApolloPerson
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

            growjo_score = sum(1 for f in growjo_fields if f and f.lower() != "not found")
            apollo_score = sum(1 for f in apollo_fields if f and f.lower() != "not found")
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

            # Determine source contribution
            used_growjo = any(
                [
                    growjo.get("revenue"),
                    growjo.get("employee_count"),
                    growjo.get("industry"),
                    growjo.get("decider_email"),
                    growjo.get("decider_name"),
                    growjo.get("company_website"),
                ]
            )

            used_apollo = any(
                [
                    apollo.get("annual_revenue_printed"),
                    apollo.get("employee_count"),
                    apollo.get("industry"),
                    apollo.get("linkedin_url"),
                    apollo.get("founded_year"),
                    apollo.get("keywords"),
                    apollo.get("business_type"),
                ]
            )

            # Assign source tag
            if used_growjo and used_apollo:
                rows_to_update.at[idx, "Source"] = "Growjo + Apollo"
            elif used_growjo:
                rows_to_update.at[idx, "Source"] = "Growjo"
            elif used_apollo:
                rows_to_update.at[idx, "Source"] = "Apollo"
            else:
                rows_to_update.at[idx, "Source"] = "N/A"

            progress_bar.progress((i + 1) / len(rows_to_update))
            status_text.text(f"Enhanced {i + 1} of {len(rows_to_update)} rows")

        for col in rows_to_update.columns:
            enhanced_df.loc[rows_to_update.index, col] = rows_to_update[col]

        # After enrichment, replace locked Apollo emails with 'N/A' in the Email column
        if "Email" in enhanced_df.columns:
            enhanced_df["Email"] = enhanced_df["Email"].replace("email_not_unlocked@domain.com", "N/A")

        elapsed_time = time.time() - start_time
        st.success(f"✅ Enrichment complete in {elapsed_time / 60:.2f} minutes!")
        st.dataframe(enhanced_df.head(), use_container_width=True)
        st.session_state.enriched_df = enhanced_df.copy()
        st.session_state.enrichment_done = True

        csv = enhanced_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Enhanced CSV", csv, file_name="enriched_leads.csv", mime="text/csv"
        )

    # Step 4: Filter Enhanced Data — OUTSIDE of the button block
    if st.session_state.get("enrichment_done") and "enriched_df" in st.session_state:
        st.markdown("### 🧹 Step 4: Filter Enhanced Data")

        enhanced_df = st.session_state.enriched_df.copy()

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            min_revenue = st.text_input(
                "Minimum Revenue (e.g., 500K, 1M, 2B)", value="", key="min_revenue_input"
            )
        with filter_col2:
            min_employees = st.number_input(
                "Minimum Employees", value=0, step=1, key="min_employees_input"
            )

        # Apply filtering
        enhanced_df["Revenue Numeric"] = enhanced_df["Revenue"].apply(revenue_to_number)
        enhanced_df["Employees Numeric"] = pd.to_numeric(
            enhanced_df["Employees count"], errors="coerce"
        ).fillna(0)

        filtered_df = enhanced_df.copy()

        if min_revenue:
            min_revenue_num = revenue_to_number(min_revenue)
            filtered_df = filtered_df[filtered_df["Revenue Numeric"] >= min_revenue_num]

        if min_employees > 0:
            filtered_df = filtered_df[filtered_df["Employees Numeric"] >= min_employees]

        # Show filtered result
        st.dataframe(
            filtered_df.drop(columns=["Revenue Numeric", "Employees Numeric"]).head(),
            use_container_width=True,
        )

        if st.button("✅ Confirm Filtered Data"):
            st.session_state.filtered_df = filtered_df.drop(
                columns=["Revenue Numeric", "Employees Numeric"]
            ).copy()
            st.success("✅ Filtered data confirmed! Proceed to select final rows.")


# Final Step: Select rows to download
if "filtered_df" in st.session_state:
    st.markdown("### 🖱️ Step 5: Select Final Rows to Download")

    filtered_data_with_select = st.session_state.filtered_df.copy()
    filtered_data_with_select["Select Row"] = False

    edited_final_df = st.data_editor(
        filtered_data_with_select,
        use_container_width=True,
        num_rows="dynamic",
        key="final_selection_editor",
        disabled=filtered_data_with_select.columns[:-1].tolist(),
    )

    selected_final_df = edited_final_df[edited_final_df["Select Row"] == True].drop(
        columns=["Select Row"]
    )

    st.markdown(f"**🧮 Selected Final Rows: `{len(selected_final_df)}`**")

    if len(selected_final_df) > 0:
        csv_final = selected_final_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Final Selected CSV",
            csv_final,
            file_name="final_selected_leads.csv",
            mime="text/csv",
        )
    else:
        st.info("Please select at least one row to enable download.")
