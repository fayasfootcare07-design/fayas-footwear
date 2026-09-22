import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import qrcode
from io import BytesIO
from PIL import Image
import json
from supabase import create_client, Client
import google.generativeai as genai

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Fayas Footwear - Dashboard",
    page_icon="👞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SECRETS & CLIENT INITIALIZATION ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Secret Configuration Error: Check your Streamlit Secrets! Details: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def get_ist_time():
    return datetime.now(ZoneInfo('Asia/Kolkata'))

def generate_qr_code(data_str):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- HEADER & BRANDING ---
st.title("👞 FAYAS FOOTWEAR")
st.caption("Live Cloud Inventory & Sales Dashboard (IST Real-Time Sync)")

# --- ACCESS CONTROL / SIDEBAR LOGIN ---
st.sidebar.title("Access Control")
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    admin_pass = st.sidebar.text_input("Enter Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if admin_pass == "Fayas786":
            st.session_state["admin_logged_in"] = True
            st.sidebar.success("Logged in as Admin!")
            st.rerun()
        else:
            st.sidebar.error("Invalid Password")
else:
    st.sidebar.success("Logged in as Admin 🔒")
    if st.sidebar.button("Logout"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# --- NAVIGATION ROUTING ---
st.sidebar.title("Navigation")
menu_options = ["📦 Live Stock", "🔥 Fast Selling Products", "📊 Sales Analytics"]

if st.session_state["admin_logged_in"]:
    menu_options.extend([
        "⚠️ Dead Stock Finder",
        "➕ Quick Sale Entry",
        "📝 Stock Update / New Entry",
        "📷 Paper Photo Stock Upload (AI Scan)"
    ])

menu = st.sidebar.radio("Go to", menu_options)

# ---------------------------------------------------------
# 1. LIVE STOCK STATUS
# ---------------------------------------------------------
if menu == "📦 Live Stock":
    st.subheader("📦 Live Stock Inventory")
    try:
        response = supabase.table("stock").select("*").execute()
        df_stock = pd.DataFrame(response.data)

        if df_stock.empty:
            st.warning("No stock data found in Supabase database. Add stock via Manual Entry or AI Paper Scan!")
        else:
            # Map possible column names safely
            prod_col = 'product_name' if 'product_name' in df_stock.columns else ('product' if 'product' in df_stock.columns else 'item_name')
            gender_col = 'gender' if 'gender' in df_stock.columns else 'category'

            if prod_col not in df_stock.columns:
                st.write("Current Stock Data Structure:")
                st.dataframe(df_stock, use_container_width=True)
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    gender_opts = df_stock[gender_col].unique() if gender_col in df_stock.columns else []
                    gender_filter = st.multiselect("Gender Category", options=gender_opts, default=gender_opts)
                with col2:
                    brand_opts = df_stock[prod_col].unique()
                    brand_filter = st.multiselect("Brand / Product", options=brand_opts, default=brand_opts)
                with col3:
                    search_art = st.text_input("Search Art No", "")

                filtered_df = df_stock.copy()
                if gender_col in df_stock.columns and gender_filter:
                    filtered_df = filtered_df[filtered_df[gender_col].isin(gender_filter)]
                if brand_filter:
                    filtered_df = filtered_df[filtered_df[prod_col].isin(brand_filter)]
                if search_art and 'art_no' in df_stock.columns:
                    filtered_df = filtered_df[filtered_df['art_no'].astype(str).str.contains(search_art, case=False, na=False)]

                st.dataframe(filtered_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching stock: {e}")

# ---------------------------------------------------------
# 2. FAST SELLING PRODUCTS
# ---------------------------------------------------------
elif menu == "🔥 Fast Selling Products":
    st.subheader("🔥 Top Selling Products")
    try:
        sales_res = supabase.table("sales").select("*").execute()
        df_sales = pd.DataFrame(sales_res.data)

        if df_sales.empty:
            st.info("No sales records available yet.")
        else:
            group_cols = [c for c in ['product_name', 'gender', 'art_no', 'size'] if c in df_sales.columns]
            if group_cols:
                fast_selling = df_sales.groupby(group_cols)['qty'].sum().reset_index()
                fast_selling = fast_selling.sort_values(by='qty', ascending=False)
                st.dataframe(fast_selling, use_container_width=True)
            else:
                st.dataframe(df_sales, use_container_width=True)

    except Exception as e:
        st.error(f"Error calculating fast-selling items: {e}")

# ---------------------------------------------------------
# 3. SALES ANALYTICS
# ---------------------------------------------------------
elif menu == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics & Revenue")
    try:
        sales_res = supabase.table("sales").select("*").execute()
        df_sales = pd.DataFrame(sales_res.data)

        if df_sales.empty:
            st.info("No sales data recorded yet.")
        else:
            df_sales['revenue'] = df_sales['qty'] * df_sales['price']
            total_qty = df_sales['qty'].sum()
            total_rev = df_sales['revenue'].sum()

            m1, m2 = st.columns(2)
            m1.metric("Total Pair Sales", f"{total_qty} Pairs")
            m2.metric("Total Revenue", f"₹{total_rev:,.2f}")

            st.write("### Recent Transactions")
            st.dataframe(df_sales.sort_values(by='created_at', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

# ---------------------------------------------------------
# 4. DEAD STOCK FINDER (ADMIN ONLY)
# ---------------------------------------------------------
elif menu == "⚠️ Dead Stock Finder" and st.session_state["admin_logged_in"]:
    st.subheader("⚠️ Low or Zero Selling Stock")
    try:
        stock_res = supabase.table("stock").select("*").execute()
        sales_res = supabase.table("sales").select("*").execute()

        df_stock = pd.DataFrame(stock_res.data)
        df_sales = pd.DataFrame(sales_res.data)

        if df_stock.empty:
            st.info("Stock inventory is empty.")
        else:
            if not df_sales.empty and 'art_no' in df_stock.columns and 'art_no' in df_sales.columns:
                sold_items = df_sales[['product_name', 'gender', 'art_no', 'size']].drop_duplicates()
                dead_stock = pd.merge(df_stock, sold_items, on=['product_name', 'gender', 'art_no', 'size'], how='left', indicator=True)
                dead_stock = dead_stock[dead_stock['_merge'] == 'left_only'].drop(columns=['_merge'])
            else:
                dead_stock = df_stock

            st.warning(f"Found {len(dead_stock)} stock items with zero sales record:")
            st.dataframe(dead_stock, use_container_width=True)

    except Exception as e:
        st.error(f"Error computing dead stock: {e}")

# ---------------------------------------------------------
# 5. QUICK SALE ENTRY (ADMIN ONLY)
# ---------------------------------------------------------
elif menu == "➕ Quick Sale Entry" and st.session_state["admin_logged_in"]:
    st.subheader("➕ Quick Sale Entry & Bill Generator")
    try:
        stock_res = supabase.table("stock").select("*").execute()
        df_stock = pd.DataFrame(stock_res.data)

        if df_stock.empty:
            st.error("No stock available to sell!")
        else:
            prod_col = 'product_name' if 'product_name' in df_stock.columns else 'product'
            with st.form("sale_form"):
                col1, col2 = st.columns(2)
                with col1:
                    product = st.selectbox("Product / Brand", df_stock[prod_col].unique())
                    sub_stock = df_stock[df_stock[prod_col] == product]
                    gender = st.selectbox("Gender", sub_stock['gender'].unique() if 'gender' in sub_stock.columns else ["Gents"])
                    if 'gender' in sub_stock.columns:
                        sub_stock = sub_stock[sub_stock['gender'] == gender]
                
                with col2:
                    art_no = st.selectbox("Art No", sub_stock['art_no'].unique() if 'art_no' in sub_stock.columns else ["N/A"])
                    if 'art_no' in sub_stock.columns:
                        sub_stock = sub_stock[sub_stock['art_no'] == art_no]
                    size = st.selectbox("Size", sub_stock['size'].unique() if 'size' in sub_stock.columns else ["N/A"])
                    
                selected_item = sub_stock.iloc[0]
                available_qty = selected_item.get('qty', 0)
                item_price = selected_item.get('price', 0.0)

                st.info(f"Available Quantity: **{available_qty}** | Price per pair: **₹{item_price}**")

                sell_qty = st.number_input("Sell Quantity", min_value=1, max_value=max(1, int(available_qty)), value=1)
                submit_sale = st.form_submit_button("🧾 Complete Sale & Generate Receipt")

            if submit_sale:
                current_ist = get_ist_time().isoformat()
                
                supabase.table("sales").insert({
                    "product_name": product,
                    "gender": gender,
                    "art_no": art_no,
                    "size": str(size),
                    "qty": int(sell_qty),
                    "price": float(item_price),
                    "created_at": current_ist
                }).execute()

                new_qty = max(0, int(available_qty) - int(sell_qty))
                supabase.table("stock").update({"qty": new_qty}).eq("id", selected_item['id']).execute()

                st.success("Sale Recorded & Stock Deducted Successfully!")

                bill_details = f"FAYAS FOOTWEAR\nDate: {get_ist_time().strftime('%d-%m-%Y %I:%M %p')}\nItem: {product} ({gender})\nArt: {art_no} | Size: {size}\nQty: {sell_qty} x ₹{item_price}\nTotal: ₹{sell_qty * item_price}"
                qr_img = generate_qr_code(bill_details)

                st.write("### 🧾 Digital Receipt")
                st.text(bill_details)
                st.image(qr_img, caption="Scan QR for Digital Bill Receipt")

    except Exception as e:
        st.error(f"Error completing sale: {e}")

# ---------------------------------------------------------
# 6. STOCK UPDATE / NEW ENTRY (ADMIN ONLY)
# ---------------------------------------------------------
elif menu == "📝 Stock Update / New Entry" and st.session_state["admin_logged_in"]:
    st.subheader("📝 Manual Stock Entry / Add New Items")
    with st.form("manual_stock_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("Brand / Product Name (e.g., Walkaroo)")
            gender = st.selectbox("Gender", ["Gents", "Ladies", "Kids"])
            art_no = st.text_input("Art No (e.g., W-102)")
        with col2:
            size = st.text_input("Size (e.g., 7 or 8)")
            qty = st.number_input("Quantity", min_value=1, value=12)
            price = st.number_input("Price (MRP)", min_value=0.0, value=350.0)

        submit_stock = st.form_submit_button("💾 Save to Stock")

        if submit_stock:
            if not product_name or not art_no or not size:
                st.error("Please fill all fields!")
            else:
                try:
                    supabase.table("stock").insert({
                        "product_name": product_name.strip(),
                        "gender": gender,
                        "art_no": art_no.strip(),
                        "size": str(size).strip(),
                        "qty": int(qty),
                        "price": float(price)
                    }).execute()
                    st.success("Stock Added Successfully!")
                except Exception as e:
                    st.error(f"Failed to add stock: {e}")

# ---------------------------------------------------------
# 7. PAPER PHOTO STOCK UPLOAD (AI SCAN - ADMIN ONLY)
# ---------------------------------------------------------
elif menu == "📷 Paper Photo Stock Upload (AI Scan)" and st.session_state["admin_logged_in"]:
    st.subheader("📷 Paper Photo Stock Upload (AI Scan)")
    st.write("Upload a photo of your handwritten or printed stock list to automatically extract and save inventory.")

    uploaded_file = st.file_uploader("Upload Stock List Photo", type=["jpg", "png", "jpeg"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Paper Photo", use_container_width=True)

        if st.button("🔴 Process Paper & Extract Stock Details"):
            with st.spinner("AI is scanning and parsing your stock photo..."):
                try:
                    # Multi-model Fallback List to ensure API model compatibility
                    model_names = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-pro-vision']
                    response = None
                    
                    prompt = """
                    Extract the stock details from this paper image and return ONLY a valid JSON array.
                    Keys required for each item:
                    - "product_name": String (e.g., Walkaroo, Paragon)
                    - "gender": String ("Gents", "Ladies", or "Kids")
                    - "art_no": String (e.g., W-102)
                    - "size": Integer or String (e.g., 7)
                    - "qty": Integer
                    - "price": Float or Integer (MRP price)

                    Return RAW JSON ONLY. No markdown formatting, no backticks, no explanatory text.
                    """

                    for m_name in model_names:
                        try:
                            model = genai.GenerativeModel(m_name)
                            response = model.generate_content([prompt, image])
                            if response and response.text:
                                break
                        except Exception:
                            continue

                    if not response or not response.text:
                        raise Exception("Could not get response from Gemini vision models. Check API Key permissions.")

                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    extracted_data = json.loads(clean_text)

                    st.session_state["extracted_stock_data"] = extracted_data
                    st.success("Successfully extracted stock items!")

                except Exception as e:
                    st.error(f"Failed to parse paper image: {e}")

    # Preview & Confirm Section
    if "extracted_stock_data" in st.session_state and st.session_state["extracted_stock_data"]:
        df_extracted = pd.DataFrame(st.session_state["extracted_stock_data"])
        st.write("### Preview Extracted Data")
        st.dataframe(df_extracted, use_container_width=True)

        if st.button("✅ Confirm & Add to Stock"):
            try:
                for item in st.session_state["extracted_stock_data"]:
                    supabase.table("stock").insert({
                        "product_name": str(item.get("product_name", "")),
                        "gender": str(item.get("gender", "Gents")),
                        "art_no": str(item.get("art_no", "")),
                        "size": str(item.get("size", "")),
                        "qty": int(item.get("qty", 0)),
                        "price": float(item.get("price", 0.0))
                    }).execute()

                st.balloons()
                st.success("All items successfully imported into Supabase Stock!")
                del st.session_state["extracted_stock_data"]
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save stock to database: {e}")
