import json
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import pandas as pd
from PIL import Image
import qrcode
from supabase import Client, create_client
import streamlit as st
import streamlit.components.v1 as components

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Fayas Footwear & Enterprises Dashboard",
    page_icon="👞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SESSION STATE FOR MULTI-SHOP ROUTING ---
if "selected_shop" not in st.session_state:
    st.session_state["selected_shop"] = None

if "shop_logged_in" not in st.session_state:
    st.session_state["shop_logged_in"] = False

# --- PAGE 1: LANDING PAGE (SHOP SELECTION) ---
if st.session_state["selected_shop"] is None:
    st.title("👞 Welcome to Footwear Management System")
    st.subheader("Select Your Shop / Branch to Continue")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏬 Fayas Footwear")
        st.info("Main Branch Inventory & Sales System")
        if st.button("Open Fayas Footwear", use_container_width=True, type="primary"):
            st.session_state["selected_shop"] = "Fayas Footwear"
            st.rerun()

    with col2:
        st.markdown("### 🩴 Lulu Chappals")
        st.success("Lulu Branch Inventory & Sales System")
        if st.button("Open Lulu Chappals", use_container_width=True, type="primary"):
            st.session_state["selected_shop"] = "Lulu Chappals"
            st.rerun()

    st.stop()

# --- PAGE 2: LOGIN PAGE FOR SELECTED SHOP ---
current_shop = st.session_state["selected_shop"]

# Set credentials according to selected shop
if current_shop == "Fayas Footwear":
    SHOP_PASSWORD = "Fayas786"
    # Fayas Supabase Secrets
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
else:
    SHOP_PASSWORD = "Lulu786"  # Set your password for Lulu Chappals
    # Lulu Supabase Secrets (or fallback to main if same database)
    SUPABASE_URL = st.secrets.get("LULU_SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
    SUPABASE_KEY = st.secrets.get("LULU_SUPABASE_KEY", st.secrets.get("SUPABASE_KEY", ""))

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Database Connection Error for {current_shop}: {e}")
    st.stop()

# Header banner with Switch Shop option
head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title(f"🏬 {current_shop.upper()}")
    st.caption("Live Cloud Inventory & Sales Dashboard")
with head_col2:
    st.write("##")
    if st.button("🔄 Switch Shop"):
        st.session_state["selected_shop"] = None
        st.session_state["shop_logged_in"] = False
        st.rerun()

# Login Form Screen (Page 2)
if not st.session_state["shop_logged_in"]:
    st.divider()
    st.subheader(f"🔒 Welcome {current_shop} Admin")
    st.write("Please enter password to access dashboard.")

    with st.form("shop_login_form"):
        entered_pass = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login to Dashboard", type="primary")

        if login_btn:
            if entered_pass == SHOP_PASSWORD:
                st.session_state["shop_logged_in"] = True
                st.session_state["admin_logged_in"] = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid Password!")

    st.stop()

# --- PAGE 3: DASHBOARD MAIN NAVIGATION (Page 3-i) ---
st.sidebar.title(f"{current_shop}")
st.sidebar.success(f"Logged in as Admin 🔒")
if st.sidebar.button("Logout"):
    st.session_state["shop_logged_in"] = False
    st.session_state["admin_logged_in"] = False
    st.rerun()

st.sidebar.title("Navigation")
