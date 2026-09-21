import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from supabase import create_client, Client

# Page Config
st.set_page_config(page_title="Fayas Footwear", page_icon="👞", layout="wide")

# JavaScript to move focus on Enter Key press
enter_to_next_js = """
<script>
const doc = window.parent.document;
doc.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        const inputs = Array.from(doc.querySelectorAll('input, select'));
        const active = doc.activeElement;
        const index = inputs.indexOf(active);
        if (index > -1 && index < inputs.length - 1) {
            e.preventDefault();
            inputs[index + 1].focus();
        }
    }
}, true);
</script>
"""
components.html(enter_to_next_js, height=0, width=0)

# Supabase Credentials Setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session State for Authentication
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Session State Keys for Auto-fill Sale Entry
if "sale_art" not in st.session_state:
    st.session_state["sale_art"] = ""
if "sale_size" not in st.session_state:
    st.session_state["sale_size"] = ""
if "sale_price" not in st.session_state:
    st.session_state["sale_price"] = 0.0

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

# --- 2. QUICK SALE ENTRY (WITH WORKING AUTO-FILL) ---
elif choice == "➕ Quick Sale Entry" and st.session_state["logged_in"]:
    st.subheader("➕ Quick Sale Entry")
    
    try:
        stock_data = supabase.table("stock").select("*").execute().data
        stock_df = pd.DataFrame(stock_data) if stock_data else pd.DataFrame()
    except:
        stock_df = pd.DataFrame()

    search_brand = st.text_input("🔍 Type Company / Brand Name (e.g., mark, paragon, vkc)")
    
    if not stock_df.empty and search_brand.strip():
        matched_df = stock_df[
            stock_df["product"].str.contains(search_brand, case=False, na=False) |
            stock_df["art_no"].str.contains(search_brand, case=False, na=False)
        ]
        
        if not matched_df.empty:
            options = ["-- Select Stock Item --"] + [
                f"{row['product']} | Art:{row['art_no']} | Size:{row['size']} | MRP: ₹{row['price']} | Stock:{row['quantity']} pairs" 
                for _, row in matched_df.iterrows()
            ]
            
            def update_sale_fields():
                selected = st.session_state["stock_selector"]
                if selected != "-- Select Stock Item --":
                    idx = options.index(selected) - 1
                    row = matched_df.iloc[idx]
                    st.session_state["sale_art"] = str(row["art_no"])
                    st.session_state["sale_size"] = str(row["size"])
                    st.session_state["sale_price"] = float(row["price"])

            st.selectbox(
                f"🎯 Available Stock Suggestions for '{search_brand}' (Select to Auto-fill):",
                options,
                key="stock_selector",
                on_change=update_sale_fields
            )
        else:
            st.warning(f"No stock found matching '{search_brand}'")

    st.divider()

    # Form Fields with Session State Connection
    art_no = st.text_input("Art No / Brand", key="sale_art")
    size = st.text_input("Size", key="sale_size")
    qty = st.number_input("Quantity Sold", min_value=1, value=1, step=1, key="sale_qty")
    price = st.number_input("Price per Unit (₹)", min_value=0.0, step=10.0, key="sale_price")
    
    if st.button("Record Sale & Deduct Stock", type="primary"):
        if not art_no:
            st.warning("Please enter or select Art No / Brand.")
        else:
            try:
                # Insert into Sales Table
                supabase.table("sales").insert({
                    "art_no": art_no, "size": size, "quantity": qty, "price": price
                }).execute()
                
                # Check matching item in Stock and Deduct Quantity
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
    
    product = st.text_input("Product Name / Brand (e.g., VKC, Paragon)", key="stock_product")
    gender = st.selectbox("Gender Category", ["Gents", "Ladies", "Kids"], key="stock_gender")
    art_no = st.text_input("Art No", key="stock_art")
    size = st.text_input("Size", key="stock_size")
    qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="stock_qty")
    price = st.number_input("Price (₹)", min_value=0.0, step=10.0, key="stock_price")
    
    if st.button("Add Stock", type="primary"):
        if not product or not art_no:
            st.warning("Please fill Product Name and Art No.")
        else:
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
