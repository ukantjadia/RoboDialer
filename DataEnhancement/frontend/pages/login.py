import streamlit as st
st.set_page_config(page_title="🔐 Login", layout="centered")   <-- FIRST Streamlit command
import requests
import jwt
from streamlit_cookies_controller import CookieController
from config import BACKEND_URL

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style/custom_theme.css")

JWT_ALGORITHM = "HS256"

cookies = CookieController()
token = cookies.get("auth_token")

if token and "logged_in" not in st.session_state:
    try:
         Decode token without verifying signature
        decoded = jwt.decode(token, options={"verify_signature": False})
        st.session_state.logged_in = True
        st.session_state.token = token
        st.session_state.username = decoded.get("username")
    except Exception:
        cookies.delete("auth_token")
        st.markdown("<span style='color:ffb347; font-weight:700; font-size:1.05rem;'>⚠️ Invalid or expired session. Please log in again.</span>", unsafe_allow_html=True)

if st.session_state.get("just_logged_in"):
    st.session_state.pop("just_logged_in")
    st.markdown(f"<span style='color:1e656d; font-weight:700; font-size:1.05rem;'>✅ Logged in as <b>{st.session_state.username}</b></span>", unsafe_allow_html=True)

elif not st.session_state.get("logged_in"):
    def login_form():
        st.markdown("""
            <style>
            body, .stApp {
                background: linear-gradient(135deg, f6f8fa 0%, e8ecf4 100%) !important;
            }
            .login-card-bg {
                background: fff;
                border-radius: 24px;
                box-shadow: 0 4px 24px rgba(30,101,109,0.08);
                max-width: 420px;
                margin: 4rem auto 2rem auto;
                padding: 2.5rem 2.5rem 2rem 2.5rem;
            }
            .stTextInput>div>div>input {
                background: 232a34 !important;
                color: fff !important;
                border-radius: 8px !important;
                border: none !important;
                font-size: 1.08rem !important;
                font-weight: 500 !important;
                padding: 0.8rem 1.1rem !important;
            }
            .stTextInput>div>div>input::placeholder {
                color: cfd8dc !important;
                opacity: 1 !important;
            }
            .forgot-link, .forgot-link a {
                color: 1e656d !important;
                font-weight: 500;
                text-decoration: underline;
            }

            </style>
        """, unsafe_allow_html=True)
        st.markdown("""
            <div class='login-card-bg' style='text-align:center;'>
                <h1 style='color:183153; font-size:2.2rem; font-weight:800; margin-bottom:0.5rem;'>👋 Welcome Back</h1>
                <div class='subtitle' style='color:183153; font-size:1.1rem; margin-bottom:2rem; font-weight:600;'>Login to enjoy all of our cool features ✌️</div>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            st.markdown("""
            <style>
            
            .custom-login-btn {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
            }
            .custom-login-btn button {
                background: e8f0fe !important;
                color: 183153 !important;
                font-weight: 800 !important;
                border: none !important;
                border-radius: 1rem !important;
                width: 180px !important;
                margin: 2rem auto 1rem auto !important;
                font-size: 1.15rem !important;
                box-shadow: 0 2px 12px rgba(24,49,83,0.10);
                text-align: center !important;
                display: block !important;
            }
            .forgot-link {
                color: fff !important;
                float: right;
                font-size: 0.98rem;
                margin-bottom: 1.2rem;
                text-decoration: underline;
                font-weight: 400;
            }
            </style>
            """, unsafe_allow_html=True)
            username = st.text_input("Email address", key="login_username", help="Enter your email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", key="login_password", help="Enter your password", placeholder="Password")
            st.markdown('<div class="forgot-link"><a href="" style="color:fff;">Forgot password?</a></div>', unsafe_allow_html=True)
             No checkbox, st.empty, or extra Streamlit widget
             Style the login button once, after the input fields
            st.markdown("""
            <style>
            .custom-login-box-btn {
                background: fff;
                color: 2196f3;
                font-weight: 800;
                border-radius: 1.5rem;
                border: 2px solid 2196f3;
                box-shadow: 0 4px 15px rgba(33, 150, 243, 0.10);
                padding: 0.9rem 0;
                width: 180px;
                margin: 2rem auto 1rem auto;
                font-size: 1.15rem;
                text-align: center;
                cursor: pointer;
                transition: background 0.2s, color 0.2s, border 0.2s;
                display: flex;
                justify-content: center;
                align-items: center;
                user-select: none;
            }
            .custom-login-box-btn:hover {
                background: e3f1fd;
                color: 1565c0;
                border: 2px solid 1565c0;
            }
            .hide-streamlit-btn > button { display: none !important; }
            </style>
            """, unsafe_allow_html=True)
             Only use the Streamlit button, styled as a white box with blue border and text
            st.markdown("""
            <style>
            .stButton > button {
                background: fff !important;
                color: 2196f3 !important;
                font-weight: 800 !important;
                border-radius: 1.5rem !important;
                border: 2px solid 2196f3 !important;
                box-shadow: 0 4px 15px rgba(33, 150, 243, 0.10);
                padding: 0.9rem 0 !important;
                width: 180px !important;
                margin: 2rem auto 1rem auto !important;
                font-size: 1.15rem !important;
                text-align: center !important;
                cursor: pointer !important;
                transition: background 0.2s, color 0.2s, border 0.2s;
                display: flex !important;
                justify-content: center;
                align-items: center;
                user-select: none;
            }
            .stButton > button:hover {
                background: e3f1fd !important;
                color: 1565c0 !important;
                border: 2px solid 1565c0 !important;
            }
            .stButton { display: flex; justify-content: center; }
            </style>
            """, unsafe_allow_html=True)
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username or not password:
                    st.markdown("<span style='color:ffb347; font-weight:700; font-size:1.05rem;'>⚠️ Please enter both email and password.</span>", unsafe_allow_html=True)
                    return
                try:
                    res = requests.post(f"{BACKEND_URL}/api/login", json={
                        "username": username,
                        "password": password
                    })
                    if res.status_code == 200:
                        token = res.json().get("token")
                        decoded = jwt.decode(token, options={"verify_signature": False})
                        st.session_state.logged_in = True
                        st.session_state.token = token
                        st.session_state.username = decoded.get("username")
                        cookies.set("auth_token", token)
                        st.session_state.just_logged_in = True
                        st.rerun()
                    else:
                        st.markdown(f"<span style='color:d7263d; font-weight:700; font-size:1.05rem;'>❌ {res.json().get('error', 'Login failed.')}</span>", unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f"<span style='color:d7263d; font-weight:700; font-size:1.05rem;'>⚠️ Failed to connect to backend: {e}</span>", unsafe_allow_html=True)

    login_form()

else:
    st.markdown(f"<span style='color:1e656d; font-weight:700; font-size:1.05rem;'>✅ You are logged in as <b>{st.session_state.username}</b></span>", unsafe_allow_html=True)
    if st.button("🔓 Logout"):
        st.session_state.clear()
        try:
            cookies.remove("auth_token")
        except KeyError:
            pass
        st.rerun()