import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
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

# Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "sale_art" not in st.session_state:
    st.session_state["sale_art"] = ""
if "sale_size" not in st.session_state:
    st.session_state["sale_size"] = ""
if "sale_price" not in st.session_state:
    st.session_state["sale_price"] = 0.0

# --- FANCY BILL RECEIPT GENERATION ---
def generate_fancy_bill_image(art_no, size, qty, price, total_amount, bill_no):
    width, height = 500, 680
    image = Image.new("RGB", (width, height), color="#FAFAFA")
    draw = ImageDraw.Draw(image)
    
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 24)
        subtitle_font = ImageFont.truetype("arial.ttf", 13)
        bold_font = ImageFont.truetype("arialbd.ttf", 15)
        text_font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        title_font = bold_font = text_font = subtitle_font = small_font = ImageFont.load_default()

    # Outer Card Border
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline="#E0E0E0", width=2)
    
    # Top Red Header
    draw.rectangle([(10, 10), (width - 10, 110)], fill="#C82333")
    draw.text((width // 2, 42), "FAYAS FOOTWEAR", fill="white", font=title_font, anchor="mm")
    draw.text((width // 2, 75), "PREMIUM FOOTWEAR COLLECTION • SINCE 2016", fill="#FFC107", font=subtitle_font, anchor="mm")

    # Invoice & Date Info
    current_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
    draw.text((30, 130), f"Invoice No : {bill_no}", fill="#333333", font=bold_font)
    draw.text((30, 155), f"Date         : {current_time}", fill="#666666", font=text_font)
    draw.text((30, 180), "Payment   : CASH (PAID)", fill="#28A745", font=bold_font)

    # Dotted Line
    for x in range(30, width - 30, 10):
        draw.line([(x, 210), (x + 5, 210)], fill="#CCCCCC", width=2)

    # Product Table Header
    draw.rectangle([(30, 225), (width - 30, 260)], fill="#F1F3F5")
    draw.text((40, 242), "ITEM / BRAND", fill="#333333", font=bold_font, anchor="lm")
    draw.text((240, 242), "SIZE", fill="#333333", font=bold_font, anchor="lm")
    draw.text((310, 242), "QTY", fill="#333333", font=bold_font, anchor="lm")
    draw.text((380, 242), "PRICE", fill="#333333", font=bold_font, anchor="lm")

    # Product Details
    draw.text((40, 285), str(art_no)[:18], fill="#222222", font=text_font, anchor="lm")
    draw.text((240, 285), str(size), fill="#222222", font=text_font, anchor="lm")
    draw.text((310, 285), str(qty), fill="#222222", font=text_font, anchor="lm")
    draw.text((380, 285), f"₹{price:,.2f}", fill="#222222", font=text_font, anchor="lm")

    for x in range(30, width - 30, 10):
        draw.line([(x, 320), (x + 5, 320)], fill="#CCCCCC", width=2)

    # Grand Total Highlight
    draw.rectangle([(30, 340), (width - 30, 400)], fill="#FFF5F5", outline="#C82333", width=2)
    draw.text((50, 370), "TOTAL AMOUNT PAID", fill="#333333", font=bold_font, anchor="lm")
    draw.text((width - 50, 370), f"₹{total_amount:,.2f}", fill="#C82333", font=title_font, anchor="rm")

    # Bottom Footer Section
    for x in range(30, width - 30, 10):
        draw.line([(x, 430), (x + 5, 430)], fill="#CCCCCC", width=2)

    draw.text((width // 2, 470), "Thank you for shopping with us!", fill="#333333", font=bold_font, anchor="mm")
    draw.text((width // 2, 500), "FAYAS FOOTWEAR • MAIN BAZAAR", fill="#555555", font=text_font, anchor="mm")
    draw.text((width // 2, 530), "Exchange valid within 7 days with this digital bill receipt", fill="#888888", font=small_font, anchor="mm")

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

# --- FUNCTION TO GENERATE LINK QR CODE ---
def generate_link_qr(url_link):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=8, border=2)
    qr.add_data(url_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#C82333", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- POPUP DIALOGS ---
@st.dialog("⚠️ Stock Alert")
def show_error_popup(message):
    st.error(message)
    if st.button("OK, Got it"):
        st.rerun()

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

nav_options = ["📦 Live Stock", "📊 Sales Analytics"]
if st.session_state["logged_in"]:
    nav_options.extend(["➕ Quick Sale Entry", "📝 Stock Update / New Entry"])

choice = st.sidebar.radio("Navigation", nav_options)

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
            col1, col2, col3 = st.columns(3)
            total_pairs = df["quantity"].sum()
            df["total_val"] = df["quantity"] * df["price"]
            total_val = df["total_val"].sum()
            low_stock_cnt = len(df[df["quantity"] <= 3])
            
            col1.metric("Total Pairs", f"{total_pairs} Pairs")
            col2.metric("Stock Valuation", f"₹ {total_val:,.2f}")
            col3.metric("Low Stock Items", f"{low_stock_cnt} Items", delta_color="inverse")
            st.divider()
            
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
    
    try:
        stock_data = supabase.table("stock").select("*").execute().data
        stock_df = pd.DataFrame(stock_data) if stock_data else pd.DataFrame()
    except Exception as e:
        stock_df = pd.DataFrame()

    if not stock_df.empty:
        db_stock_options = [
            f"{row['product']} | Art:{row['art_no']} | Size:{row['size']} | MRP: ₹{row['price']} | Stock:{row['quantity']} pairs" 
            for _, row in stock_df.iterrows()
        ]
        
        def on_stock_select():
            selected = st.session_state["search_stock_item"]
            if selected:
                idx = db_stock_options.index(selected)
                row = stock_df.iloc[idx]
                st.session_state["sale_art"] = str(row["art_no"])
                st.session_state["sale_size"] = str(row["size"])
                st.session_state["sale_price"] = float(row["price"])

        st.selectbox(
            "🔍 Search Database Stock:",
            options=db_stock_options,
            index=None,
            placeholder="Type brand name or art no here...",
            key="search_stock_item",
            on_change=on_stock_select
        )
    else:
        st.info("No stock available in database inventory.")

    st.divider()

    art_no = st.text_input("Art No / Brand", key="sale_art")
    size = st.text_input("Size", key="sale_size")
    qty = st.number_input("Quantity Sold", min_value=1, value=1, step=1, key="sale_qty")
    price = st.number_input("Price per Unit (₹)", min_value=0.0, step=10.0, key="sale_price")
    
    st.divider()
    btn_col1, btn_col2 = st.columns(2)
    
    record_only = btn_col1.button("⚡ Record Sale Only", type="secondary", use_container_width=True)
    record_and_bill = btn_col2.button("🧾 Record Sale & Generate Bill QR", type="primary", use_container_width=True)

    if record_only or record_and_bill:
        if not art_no:
            show_error_popup("Please enter or select Art No / Brand.")
        else:
            try:
                stock_res = supabase.table("stock").select("*").eq("size", size).execute()
                matched_item = None
                
                if stock_res.data:
                    for item in stock_res.data:
                        if (art_no.lower() in str(item.get("art_no", "")).lower()) or \
                           (art_no.lower() in str(item.get("product", "")).lower()):
                            matched_item = item
                            break
                
                if not matched_item:
                    show_error_popup("❌ Cannot record sale!\n\nThis item & size is NOT FOUND in stock inventory.")
                elif matched_item["quantity"] < qty:
                    show_error_popup(f"⚠️ Insufficient Stock!\n\nAvailable Stock: {matched_item['quantity']} pairs\nRequested Quantity: {qty} pairs")
                else:
                    # Record Sale in Database
                    supabase.table("sales").insert({
                        "art_no": art_no, "size": size, "quantity": qty, "price": price
                    }).execute()
                    
                    # Deduct Stock Quantity
                    current_qty = matched_item["quantity"]
                    new_qty = current_qty - qty
                    supabase.table("stock").update({"quantity": new_qty}).eq("id", matched_item["id"]).execute()
                    
                    st.success(f"✅ Sale Recorded! Stock updated from {current_qty} to {new_qty} pairs.")
                    
                    # If user clicked Bill QR button, generate image & upload
                    if record_and_bill:
                        bill_no = f"FFW-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        total_amount = qty * price
                        bill_bytes = generate_fancy_bill_image(art_no, size, qty, price, total_amount, bill_no)
                        
                        file_path = f"{bill_no}.png"
                        supabase.storage.from_("bills").upload(file_path, bill_bytes, {"content-type": "image/png"})
                        
                        public_url = supabase.storage.from_("bills").get_public_url(file_path)
                        qr_bytes = generate_link_qr(public_url)
                        
                        st.divider()
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown("### 📲 Customer QR Code")
                            st.image(qr_bytes, caption="Scan to open full colorful bill on phone", width=250)
                            
                        with col2:
                            st.markdown("### 🧾 Bill Image Preview")
                            st.image(bill_bytes, caption="Official Fayas Footwear Digital Receipt", width=300)

            except Exception as e:
                show_error_popup(f"Failed to record sale: {e}")

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
            show_error_popup("Please fill Product Name and Art No.")
        else:
            try:
                supabase.table("stock").insert({
                    "product": product, "gender": gender, "art_no": art_no,
                    "size": size, "quantity": qty, "price": price
                }).execute()
                st.success("✅ New stock item added successfully!")
            except Exception as e:
                show_error_popup(f"Failed to add stock: {e}")

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
