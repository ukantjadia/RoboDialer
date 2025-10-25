import streamlit as st
import pandas as pd
import asyncio
import sys
import os

os.system('playwright install chromium')

# Import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import fetch_and_merge_data
from backend.services.parser import parse_address  # <-- Address parser

st.set_page_config(page_title="LeadGenAI", layout="wide")
st.title("📊 LeadGen AI Tool")

st.markdown("#### Welcome to Caprae Capital's LeadGenAI Tool! 🐐")
st.markdown("Add your target industry and location to the sidebar, and hit '🚀 Fetch Leads'.")

# --- State Initialization ---
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame()
if 'industry_filter_selection' not in st.session_state:
    st.session_state.industry_filter_selection = []
if "edited_data" not in st.session_state:
    st.session_state.edited_data = pd.DataFrame()
if "enriched_data" not in st.session_state:
    st.session_state.enriched_data = pd.DataFrame()
if "is_scraping" not in st.session_state:
    st.session_state.is_scraping = False


# --- Sidebar Inputs ---
st.sidebar.header("🔍 Search Criteria")
industry = st.sidebar.text_input("Industry", placeholder="e.g. dentist")
location = st.sidebar.text_input("Location", placeholder="e.g. San Diego, CA")
fetch_button = st.sidebar.button("🚀 Fetch Leads", disabled = st.session_state.is_scraping)
st.sidebar.write("⚠️ Instructions:")
st.sidebar.write("1. Enter your target industry and location.")
st.sidebar.write("2. Click '🚀 Fetch Leads'.")
st.sidebar.write("3. Filter, edit, and download your leads!")
st.sidebar.write("4. Click '📄 Get Overviews' to enrich leads with company overviews.")
st.sidebar.write("5. Click '🔍 Enrich Contact Info' to enrich leads with contact info.")
st.sidebar.write("6. Click '📥 Download as CSV' to download your leads.")
st.sidebar.write("📝 Note:")
st.sidebar.write("1. Average expected time for fetching leads is 1-2 minutes.")
st.sidebar.write("2. Any lead enrichment or overview generation on a large dataset (>30 entries at a time) may take some time or crash the website.")
st.sidebar.write("3. Data may be misleading or incorrect. Please verify before exporting it.")
st.sidebar.write("4. If any unexpected errors occur, please refresh the page and try again.")

# --- Fetch Leads ---
if fetch_button and not st.session_state.is_scraping:
    st.session_state.is_scraping = True  # Immediately set before any other logic
    st.rerun()
if st.session_state.is_scraping and not fetch_button:
    with st.spinner("Scraping and merging data..."):
        raw_data = asyncio.run(fetch_and_merge_data(industry, location))
        df = pd.DataFrame(raw_data)
        st.session_state.raw_data = df
        st.session_state.enriched_data = pd.DataFrame()  # Reset enrichment
        st.session_state.industry_filter_selection = df["Industry"].dropna().unique().tolist()
    st.session_state.is_scraping = False
    st.rerun()

def _merge_enrichment(new_rows: pd.DataFrame):
    if st.session_state.enriched_data.empty:
        st.session_state.enriched_data = new_rows
    else:
        # Update only the rows that are being enriched
        st.session_state.enriched_data = pd.concat(
            [st.session_state.enriched_data, new_rows], 
            ignore_index=True
        ).drop_duplicates(subset="Company", keep="last")
# import gc
# import objgraph

# if st.button("🧹 Check for Memory Leaks"):
#     for o in gc.get_objects():
#         if 'session_state.SessionState' in str(type(o)) and o is not st.session_state:
#             st.write("SessionState reference retained by: ", type(o))
            
#             chain = objgraph.find_backref_chain(o, objgraph.is_proper_module)
#             st.write("Backref chain:")
#             for item in chain:
#                 st.write(f"→ {type(item)}")

# --- Display Leads + Filters ---
if not st.session_state.raw_data.empty:
    df = st.session_state.raw_data
    st.markdown("### 🎯 Filter by Industry")

    industry_options = df["Industry"].dropna().unique().tolist()

    # Select/Deselect All Buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Select All"):
            st.session_state.industry_filter_selection = industry_options
            st.rerun()
    with col2:
        if st.button("❌ Deselect All"):
            st.session_state.industry_filter_selection = []
            st.rerun()

    st.markdown(
        "<style>div[data-baseweb=select] { max-height: 100px; overflow-y: auto; }</style>",
        unsafe_allow_html=True
    )

    selected_industries = st.multiselect(
        label="Filter by Industry",
        options=industry_options,
        default=st.session_state.industry_filter_selection,
        key="industry_multiselect",
        label_visibility="collapsed"
    )

    # Filter
    filtered_df = df[df["Industry"].isin(selected_industries)] if selected_industries else df.iloc[0:0]

    # Merge in enriched data (if any)
    if not st.session_state.enriched_data.empty:
        merged = pd.merge(
            filtered_df, 
            st.session_state.enriched_data, 
            on="Company", 
            how="left", 
            suffixes=('', '_enriched')
        )

        for col in ["Overview", "Products & Services", "Management", "Website"]:
            if f"{col}_enriched" in merged.columns:
                # Only update the column if the enriched value is not null
                merged[col] = merged[f"{col}_enriched"].combine_first(merged[col])

        display_df = merged.drop(columns=[c for c in merged.columns if c.endswith("_enriched")])
    else:
        display_df = filtered_df

    st.markdown("### 📋 Leads Table")
    st.markdown(f"Total leads: {len(display_df)}")

    if "Company" in display_df.columns:
        display_df = display_df.sort_values(by="Company", key=lambda col: col.str.lower(), na_position='last').reset_index(drop=True)

    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        key="leads_table",
        num_rows="dynamic",
        hide_index=True
    )
    st.session_state.edited_data = edited_df

    # --- Only sync deletions if a row was actually deleted ---
    if len(edited_df) < len(display_df):
        # Assuming "Company" is a unique identifier
        st.session_state.raw_data = st.session_state.raw_data[
            st.session_state.raw_data["Company"].isin(edited_df["Company"])
        ].reset_index(drop=True)

    # --- Get Overviews ---
    if st.button("📄 Get Overviews"):
        if edited_df.empty:
            st.warning("No leads to enrich.")
        elif len(edited_df) > 50:
            st.session_state.confirm_overview = True
        else:
            st.session_state.confirm_overview = False
            st.session_state.proceed_overview = True

    # Handle Confirmation Popup
    if st.session_state.get("confirm_overview", False):
        st.warning(f"You are trying to scrape {len(edited_df)} leads. This will take some time. Are you sure you wish to continue?")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Yes, continue"):
                st.session_state.confirm_overview = False
                st.session_state.proceed_overview = True
        with col2:
            if st.button("❌ No, cancel"):
                st.session_state.confirm_overview = False
                st.info("Action cancelled.")
                st.rerun()

    # Proceed if confirmed
    if st.session_state.get("proceed_overview", False):
        st.session_state.proceed_overview = False  # Reset after action
        st.info("Scraping overviews...")

        # async def enrich_selected(df):
        #     from backend.services.overview_scraper import AsyncCompanyScraper
        #     scraper = AsyncCompanyScraper(api_key=st.secrets["OPENAI_API_KEY"])
        #     enriched_rows = []

        #     for _, row in df.iterrows():
        #         name = row.get("Name", "")
        #         location = row.get("Address") or row.get("City", "")
        #         row_dict = row.to_dict()
        #         try:
        #             enriched = await scraper.process_company(name, location)
        #             row_dict.update(enriched)
        #         except Exception as e:
        #             row_dict["Overview"] = "Error"
        #             row_dict["Products & Services"] = "Error"
        #             print(f"Overview error for {name}: {e}")
        #         enriched_rows.append(row_dict)
        #     return pd.DataFrame(enriched_rows)
        
        async def enrich_selected(df):
            from backend.services.overview_scraper import AsyncCompanyScraper
            scraper = AsyncCompanyScraper(api_key=st.secrets["OPENAI_API_KEY"])

            companies = df.to_dict(orient="records")  # Convert dataframe to list of dicts
            location = ""  # Or you can pull this from elsewhere if you prefer

            try:
                enriched_companies = await scraper.process_all_companies(companies, location)
                enriched_df = pd.DataFrame(enriched_companies)
                return enriched_df
            except Exception as e:
                print(f"Error during batch enrichment: {e}")
                return pd.DataFrame()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        enriched_df = loop.run_until_complete(enrich_selected(edited_df))
        loop.close()

        _merge_enrichment(enriched_df)
        st.success("✅ Overviews added successfully!")
        st.rerun()

    # --- Enrich Contact Info (Website + Management) ---
    if st.button("🔍 Enrich Contact Info"):
        if edited_df.empty:
            st.warning("No leads to enrich.")
        elif len(edited_df) > 50:
            st.session_state.confirm_contact = True
        else:
            st.session_state.confirm_contact = False
            st.session_state.proceed_contact = True

    # Handle Confirmation Popup for Contact Info
    if st.session_state.get("confirm_contact", False):
        st.warning(f"You are trying to enrich contact info for {len(edited_df)} leads. This will take some time. Are you sure you wish to continue?")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Yes, continue"):
                st.session_state.confirm_contact = False
                st.session_state.proceed_contact = True
        with col2:
            if st.button("❌ No, cancel"):
                st.session_state.confirm_contact = False
                st.info("Action cancelled.")
                st.rerun()

    # Proceed if confirmed
    if st.session_state.get("proceed_contact", False):
        st.session_state.proceed_contact = False  # Reset after action
        st.info("Enriching website, rating, and management info...")

        # Run the enrichment
        from backend.services.update_fields import enrich_leads
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        enriched_df = loop.run_until_complete(enrich_leads(edited_df, location))
        loop.close()

        _merge_enrichment(enriched_df)
        st.success("✅ Contact info enriched!")
        st.rerun()
    # --- Download ---
    st.download_button(
        "📥 Download as CSV",
        data=st.session_state.edited_data.to_csv(index=False),
        file_name="leads.csv",
        mime="text/csv"
    )