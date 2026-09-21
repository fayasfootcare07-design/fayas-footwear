import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Page config
st.set_page_config(page_title="Fayas Footwear", page_icon="👞", layout="centered")

# Supabase Initialization
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    SUPABASE_URL = "https://your-supabase-url.supabase.co"
    SUPABASE_KEY = "your-supabase-anon-key"
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("👞 FAYAS FOOTWEAR")
st.caption("Live Cloud Inventory & Sales Dashboard")

# Admin Session Memory Management
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

st.sidebar.title("🔐 Access Control")

# Admin Login/Logout System
if not st.session_state["admin_logged_in"]:
    pwd_input = st.sidebar.text_input("Enter Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if pwd_input == "Fayas786":
            st.session_state["admin_logged_in"] = True
            st.sidebar.success("Logged in successfully!")
            st.rerun()
        else:
            st.sidebar.error("Incorrect Password!")
else:
    st.sidebar.success("Logged in as Admin 🔓")
    if st.sidebar.button("Logout"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

is_admin = st.session_state["admin_logged_in"]

# Navigation Menu
menu_options = ["📦 Live Stock", "📊 Sales Analytics"]
if is_admin:
    menu_options.append("➕ Quick Sale Entry")
    menu_options.append("📝 Stock Update / New Entry")

choice = st.sidebar.radio("Navigation", menu_options)

# 1. LIVE STOCK VIEW
if choice == "📦 Live Stock":
    st.subheader("📦 Live Stock Status")
    try:
        response = supabase.table("stock").select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No stock data found.")
    except Exception as e:
        st.error(f"Error fetching stock: {e}")

# 2. SALES ANALYTICS VIEW
elif choice == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics")
    try:
        response = supabase.table("sales").select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sales records found.")
    except Exception as e:
        st.error(f"Error fetching sales: {e}")

# 3. QUICK SALE ENTRY (ADMIN ONLY)
elif choice == "➕ Quick Sale Entry" and is_admin:
    st.subheader("➕ Record New Sale")
    with st.form("sale_form"):
        art_no = st.text_input("Art No / Model")
        size = st.text_input("Size")
        qty = st.number_input("Quantity Sold", min_value=1, value=1)
        price = st.number_input("Price per Pair", min_value=0, value=0)
        submitted = st.form_submit_button("Save Sale")
        
        if submitted:
            data = {"art_no": art_no, "size": size, "quantity": qty, "price": price}
            try:
                supabase.table("sales").insert(data).execute()
                st.success("Sale entry saved successfully!")
            except Exception as e:
                st.error(f"Error saving sale: {e}")

# 4. STOCK UPDATE (ADMIN ONLY)
elif choice == "📝 Stock Update / New Entry" and is_admin:
    st.subheader("📝 Add / Update Stock")
    with st.form("stock_form"):
        product = st.text_input("Brand / Product Name (e.g., VKC)")
        gender = st.selectbox("Gender", ["gents", "ladies", "kids"])
        art_no = st.text_input("Art No")
        size = st.text_input("Size")
        qty = st.number_input("Stock Quantity", min_value=1, value=1)
        price = st.number_input("Selling Price", min_value=0, value=0)
        
        submitted = st.form_submit_button("Update Stock")
        if submitted:
            data = {
                "product": product,
                "gender": gender,
                "art_no": art_no,
                "size": size,
                "quantity": qty,
                "price": price
            }
            try:
                supabase.table("stock").insert(data).execute()
                st.success("Stock updated successfully in Supabase!")
            except Exception as e:
                st.error(f"Error updating stock: {e}")
