
import streamlit as st
st.set_page_config(page_title="Company Intelligence Tool", layout="wide")
from streamlit_elements import elements, mui, html
import hydralit_components as hc
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style/custom_theme.css")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in first.")
    st.stop()


 Hydralit NavBar for modern navigation (fixed API usage)
menu_data = [
    {'icon': "fa fa-home", 'label': "Main", 'id': 'main'},
    {'icon': "fa fa-upload", 'label': "Upload", 'id': 'upload'},
    {'icon': "fa fa-sign-in", 'label': "Login", 'id': 'login'},
]
over_theme = {
    'txc_inactive': 'FFFFFF',
    'menu_background': '183153',
    'txc_active': 'ff6f61',
    'option_active': 'ffb347',
    'option_background': '1e656d',
    'pg_content_bg': 'f6f8fa',
    'icon_color': 'fff',
    'font_family': 'Segoe UI,Roboto,Arial,sans-serif',
}
menu_id = hc.nav_bar(
    menu_definition=menu_data,
    override_theme=over_theme,
    home_name='Main',
    hide_streamlit_markers=False,
    sticky_nav=True,
    sticky_mode='pinned',
)
 Navbar page switching
if menu_id == 'upload':
    st.switch_page('pages/upload.py')
elif menu_id == 'login':
    st.switch_page('pages/login.py')
 Add login/logout button at the top right
from streamlit_elements import mui
with elements("navbar-login-btn"):
    if "logged_in" in st.session_state and st.session_state.logged_in:
        if mui.Button('Logout', color='error', variant='contained', sx={"float": "right", "marginTop": "-3.5rem", "marginRight": "2rem"}, onClick=lambda: st.session_state.clear() or st.rerun()):
            pass
    else:
        if mui.Button('Login', color='success', variant='contained', sx={"float": "right", "marginTop": "-3.5rem", "marginRight": "2rem"}, onClick=lambda: st.switch_page('pages/login.py')):
            pass
 Animated login success popup
if st.session_state.get("just_logged_in"):
    from hydralit_components import hy_loader
    hy_loader('Login Successful!', animation=True, color='1e656d')
    st.session_state.pop("just_logged_in")

 Material UI Card with fade-in animation for main dashboard content
with elements("main-dashboard-card"):
    mui.Card(
        [
            mui.CardHeader(title="🚀 Welcome to LeadGenAI"),
            mui.CardContent(
                html.div([
                    html.p("""
                        LeadGenAI is your all-in-one platform for automated lead enrichment and intelligent data processing.\n
                        Powered by Caprae Capital Partners.
                    """, style={"fontSize": "1.1rem", "color": "1e656d", "textAlign": "center"}),
                    html.hr(),
                    html.h3("How It Works", style={"color": "183153"}),
                    html.ol([
                        html.li("Upload your leads CSV file."),
                        html.li("Select and normalize your data."),
                        html.li("Enrich with Apollo, LinkedIn, and Growjo data."),
                        html.li("Download your enhanced leads and start connecting!")
                    ]),
                    html.h3("Key Features", style={"color": "183153"}),
                    html.ul([
                        html.li("🔍 Data Enrichment: Instantly pull company info from Apollo, LinkedIn, and Growjo."),
                        html.li("🧹 Smart Normalization: Clean and standardize your data with ease."),
                        html.li("📥 Easy CSV Upload/Download: Simple drag-and-drop interface."),
                        html.li("🛡️ Secure & Private: Your data is protected with JWT authentication.")
                    ]),
                    html.h3("Why LeadGenAI?", style={"color": "183153"}),
                    html.ul([
                        html.li("🚀 Save hours of manual research."),
                        html.li("🎯 Get richer, more accurate company profiles."),
                        html.li("🤝 Focus on outreach, not data wrangling.")
                    ]),
                    html.div(
                        "Need help or want to suggest a feature? Contact us at support@capraecapital.com or use the feedback option in the sidebar!",
                        style={"background": "f6f8fa", "padding": "1rem", "marginTop": "1rem", "borderRadius": "0.5rem", "color": "183153", "textAlign": "center"}
                    ),
                    html.hr(),
                    html.div("© 2025 Caprae Capital Partners", style={"textAlign": "center", "color": "888", "marginTop": "1rem"})
                ], style={"animation": "fadein 1s"})
            )
        ],
        sx={"maxWidth": 700, "margin": "2rem auto", "boxShadow": 3, "borderRadius": "1.5rem"}
    )
