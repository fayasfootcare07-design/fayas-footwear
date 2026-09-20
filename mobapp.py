import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Supabase Connection
SUPABASE_URL = "https://wcyhspgdtwahmymvmndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndjeWhzcGdkdHdhaG15bXZtbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk5MDEzNjUsImV4cCI6MjEwNTQ3NzM2NX0.5an7raOBnK2FYY1SZf316Q8Ah76iJe5Cz8NjSXFrhWQ"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="FAYAS FOOTWEAR - Mobile Dashboard", layout="wide")
st.title("👟 FAYAS FOOTWEAR")
st.caption("Live Cloud Inventory & Sales Dashboard")

menu = st.sidebar.radio("Navigation", ["📦 Live Stock", "📊 Sales Analytics", "➕ Quick Sale Entry"])

if menu == "📦 Live Stock":
    st.subheader("📦 Live Stock Status")
    try:
        res = supabase.table("inventory").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df, use_container_width=True)
            
            # Low Stock Alert
            low_stock = df[df['quantity'] <= 2]
            if not low_stock.empty:
                st.error("⚠️ Low Stock Alert (Quantity <= 2)")
                st.dataframe(low_stock)
        else:
            st.info("No stock data found.")
    except Exception as e:
        st.error(f"Error loading stock: {e}")

elif menu == "📊 Sales Analytics":
    st.subheader("📊 Live Sales Report")
    try:
        res = supabase.table("sales").select("*").order("id", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.metric("Total Overall Collection", f"₹ {df['amount'].sum():,.2f}")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sales records found.")
    except Exception as e:
        st.error(f"Error loading sales: {e}")

elif menu == "➕ Quick Sale Entry":
    st.subheader("➕ Mobile Sale Entry")
    with st.form("mobile_sale_form"):
        product = st.text_input("Product Name")
        gender = st.selectbox("Gender", ["Gents", "Ladies", "Kids"])
        art_no = st.text_input("Art No")
        size = st.text_input("Size")
        payment_type = st.radio("Payment Type", ["Cash", "UPI"], horizontal=True)
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        
        submitted = st.form_submit_button("Save & Sync Sale")

        if submitted:
            if product and art_no and size and amount > 0:
                sale_data = {
                    "product": product,
                    "gender": gender,
                    "art_no": art_no,
                    "size": size,
                    "payment_type": payment_type,
                    "amount": amount
                }
                supabase.table("sales").insert(sale_data).execute()
                st.success("✅ Sale Saved & Synced to Cloud!")
            else:
                st.warning("Please fill all required fields.")