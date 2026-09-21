import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Page Config
st.set_page_config(page_title="Fayas Footwear", page_icon="👞", layout="wide")

# Supabase Credentials Setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session State for Authentication
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- SIDEBAR ACCESS CONTROL ---
st.sidebar.title("🔐 Access Control")

if not st.session_state["logged_in"]:
    admin_password = st.sidebar.text_input("Enter Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if admin_password == "Fayas786":
            st.session_state["logged_in"] = True
            st.sidebar.success("Logged in as Admin 🔓")
            st.rerun()
        else:
            st.sidebar.error("Incorrect Password")
else:
    st.sidebar.success("Logged in as Admin 🔒")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

# Sidebar Navigation Options
nav_options = ["📦 Live Stock", "📊 Sales Analytics"]
if st.session_state["logged_in"]:
    nav_options.extend(["➕ Quick Sale Entry", "📝 Stock Update / New Entry"])

choice = st.sidebar.radio("Navigation", nav_options)

# --- HEADER ---
st.title("👞 FAYAS FOOTWEAR")
st.caption("Live Cloud Inventory & Sales Dashboard")

# --- 1. LIVE STOCK PAGE ---
if choice == "📦 Live Stock":
    st.subheader("📦 Live Stock Status")
    
    try:
        response = supabase.table("stock").select("*").execute()
        data = response.data
        
        if data:
            df = pd.DataFrame(data)
            
            # --- KPI METRICS TOP SUMMARY ---
            col1, col2, col3 = st.columns(3)
            total_pairs = df["quantity"].sum()
            df["total_val"] = df["quantity"] * df["price"]
            total_val = df["total_val"].sum()
            low_stock_cnt = len(df[df["quantity"] <= 3])
            
            col1.metric("Total Pairs", f"{total_pairs} Pairs")
            col2.metric("Stock Valuation", f"₹ {total_val:,.2f}")
            col3.metric("Low Stock Items", f"{low_stock_cnt} Items", delta_color="inverse")
            
            st.divider()
            
            # --- SEARCH & FILTER BAR ---
            col_s1, col_s2 = st.columns(2)
            search_art = col_s1.text_input("🔍 Search Art No / Product")
            gender_filter = col_s2.selectbox("Filter Gender", ["All", "Gents", "Ladies", "Kids"])
            
            filtered_df = df.copy()
            if search_art:
                filtered_df = filtered_df[
                    filtered_df["art_no"].str.contains(search_art, case=False, na=False) | 
                    filtered_df["product"].str.contains(search_art, case=False, na=False)
                ]
            if gender_filter != "All":
                filtered_df = filtered_df[filtered_df["gender"] == gender_filter]
                
            # --- DISPLAY TABLE ---
            st.dataframe(
                filtered_df[["product", "gender", "art_no", "size", "quantity", "price"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No stock data found.")
    except Exception as e:
        st.error(f"Error fetching stock: {e}")

# --- 2. QUICK SALE ENTRY ---
elif choice == "➕ Quick Sale Entry" and st.session_state["logged_in"]:
    st.subheader("➕ Quick Sale Entry")
    
    # Existing Stock List Select Box Option for easy selection
    try:
        stock_data = supabase.table("stock").select("*").execute().data
        if stock_data:
            stock_df = pd.DataFrame(stock_data)
            items_list = [f"{row['product']} - Art:{row['art_no']} (Size: {row['size']})" for _, row in stock_df.iterrows()]
            selected_item = st.selectbox("Select Existing Item from Stock (Optional)", ["-- Custom / Manual Entry --"] + items_list)
        else:
            stock_df = pd.DataFrame()
            selected_item = "-- Custom / Manual Entry --"
    except:
        stock_df = pd.DataFrame()
        selected_item = "-- Custom / Manual Entry --"

    with st.form("sale_form"):
        if selected_item != "-- Custom / Manual Entry --" and not stock_df.empty:
            matched_row = stock_df[stock_df.apply(lambda r: f"{r['product']} - Art:{r['art_no']} (Size: {r['size']})" == selected_item, axis=1)].iloc[0]
            default_art = str(matched_row['art_no'])
            default_size = str(matched_row['size'])
            default_price = float(matched_row['price'])
        else:
            default_art, default_size, default_price = "", "", 0.0

        art_no = st.text_input("Art No / Brand", value=default_art)
        size = st.text_input("Size", value=default_size)
        qty = st.number_input("Quantity Sold", min_value=1, value=1, step=1)
        price = st.number_input("Price per Unit (₹)", min_value=0.0, value=default_price, step=10.0)
        
        submitted = st.form_submit_button("Record Sale & Deduct Stock")
        if submitted:
            try:
                # Insert to Sales Table
                supabase.table("sales").insert({
                    "art_no": art_no, "size": size, "quantity": qty, "price": price
                }).execute()
                
                # Flexible Search: Check matching Art No or Product Name with Size
                stock_res = supabase.table("stock").select("*").eq("size", size).execute()
                matched_item = None
                
                if stock_res.data:
                    for item in stock_res.data:
                        if (art_no.lower() in str(item.get("art_no", "")).lower()) or \
                           (art_no.lower() in str(item.get("product", "")).lower()):
                            matched_item = item
                            break
                
                if matched_item:
                    current_qty = matched_item["quantity"]
                    new_qty = max(0, current_qty - qty)
                    supabase.table("stock").update({"quantity": new_qty}).eq("id", matched_item["id"]).execute()
                    st.success(f"✅ Sale Recorded! Stock updated from {current_qty} to {new_qty}.")
                else:
                    st.warning("⚠️ Sale recorded, but matching item/size not found in Stock to deduct.")
            except Exception as e:
                st.error(f"Failed to record sale: {e}")

# --- 3. STOCK UPDATE / NEW ENTRY ---
elif choice == "📝 Stock Update / New Entry" and st.session_state["logged_in"]:
    st.subheader("📝 Add / Update Inventory")
    
    with st.form("stock_form"):
        product = st.text_input("Product Name / Brand (e.g., VKC, Paragon)")
        gender = st.selectbox("Gender Category", ["Gents", "Ladies", "Kids"])
        art_no = st.text_input("Art No")
        size = st.text_input("Size")
        qty = st.number_input("Quantity", min_value=1, value=10, step=1)
        price = st.number_input("Price (₹)", min_value=0.0, step=10.0)
        
        submitted = st.form_submit_button("Add Stock")
        if submitted:
            try:
                supabase.table("stock").insert({
                    "product": product, "gender": gender, "art_no": art_no,
                    "size": size, "quantity": qty, "price": price
                }).execute()
                st.success("✅ New stock item added successfully!")
            except Exception as e:
                st.error(f"Failed to add stock: {e}")

# --- 4. SALES ANALYTICS ---
elif choice == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics & History")
    try:
        sales_res = supabase.table("sales").select("*").execute()
        if sales_res.data:
            sdf = pd.DataFrame(sales_res.data)
            sdf["total"] = sdf["quantity"] * sdf["price"]
            
            st.metric("Total Sales Generated", f"₹ {sdf['total'].sum():,.2f}")
            st.dataframe(sdf[["created_at", "art_no", "size", "quantity", "price", "total"]], use_container_width=True)
        else:
            st.info("No sales recorded yet.")
    except Exception as e:
        st.error(f"Error fetching sales: {e}")
