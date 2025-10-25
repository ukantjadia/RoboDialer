# import streamlit as st
# import os
# from dotenv import load_dotenv
# from streamlit_cookies_controller import CookieController

# load_dotenv()

# ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
# ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "caprae@123")

# st.set_page_config(page_title="🔐 Login", layout="centered")

# cookies = CookieController()


# def login_form():
#     st.markdown(
#         """
#         <style>
#             .login-card {
#                 background-color: #f9f9f9;
#                 padding: 2rem;
#                 border-radius: 1rem;
#                 box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
#                 max-width: 400px;
#                 margin: 4rem auto;
#             }
#             .login-title {
#                 text-align: center;
#                 font-size: 1.8rem;
#                 font-weight: bold;
#                 margin-bottom: 1rem;
#             }
#             .login-info {
#                 font-size: 0.9rem;
#                 color: #888;
#                 text-align: center;
#                 margin-bottom: 1.5rem;
#             }
#         </style>
#     """,
#         unsafe_allow_html=True,
#     )

#     with st.container():
#         st.markdown('<div class="login-card">', unsafe_allow_html=True)
#         st.markdown('<div class="login-title">🔐 Welcome Back</div>', unsafe_allow_html=True)
#         st.markdown(
#             '<div class="login-info">Please log in to continue</div>', unsafe_allow_html=True
#         )

#         username = st.text_input("👤 Username")
#         password = st.text_input("🔒 Password", type="password")
#         login_btn = st.button("🚀 Login")

#         st.markdown("</div>", unsafe_allow_html=True)

#         if login_btn:
#             if not username or not password:
#                 st.warning("Please enter both username and password.")
#                 return

#             if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
#                 st.session_state.logged_in = True
#                 st.session_state.username = username
#                 cookies.set("auth_token", "dummy-token")  # optional
#                 st.session_state.just_logged_in = True
#                 st.rerun()
#             else:
#                 st.error("❌ Invalid credentials.")


# # Session logic
# if st.session_state.get("just_logged_in"):
#     st.session_state.pop("just_logged_in")
#     st.success(f"✅ Logged in as **{st.session_state.username}**")

# elif not st.session_state.get("logged_in"):
#     login_form()
# else:
#     st.success(f"✅ You are logged in as **{st.session_state.username}**")
#     if st.button("🔓 Logout"):
#         st.session_state.clear()
#         cookies.remove("auth_token")
#         st.rerun()
