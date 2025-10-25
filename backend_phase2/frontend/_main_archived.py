import streamlit as st

st.set_page_config(page_title="Company Intelligence Tool", layout="wide")


# st.sidebar.title("🔍 Navigation")
# st.sidebar.markdown("Choose a feature to use:")

# ✅ Optional navigation (remove auto-switch)
if st.sidebar.button("📤 Upload CSV"):
    st.switch_page("pages/upload.py")
