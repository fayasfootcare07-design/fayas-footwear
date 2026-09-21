import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import pytz
from supabase import create_client, Client

# --- INDIA TIMEZONE (IST) SETUP ---
IST = pytz.timezone('Asia/Kolkata')

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

# Session State Initializations
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "sale_art" not in st.session_state:
    st.session_state["sale_art"] = ""
if "sale_gender" not in st.session_state:
    st.session_state["sale_gender"] = "Gents"
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

    draw.rectangle([(10, 10), (width - 10, height - 10)], outline="#E0E0E0", width=2)
    draw.rectangle([(10, 10), (width - 10, 110)], fill="#C82333")
    draw.text((width // 2, 42), "FAYAS FOOTWEAR", fill="white", font=title_font, anchor="mm")
    draw.text((width // 2, 75), "PREMIUM FOOTWEAR COLLECTION • SINCE 2016", fill="#FFC107", font=subtitle_font, anchor="mm")

    # Current Exact India Time (IST)
    current_time = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")
    draw.text((30, 130), f"Invoice No : {bill_no}", fill="#333333", font=bold_font)
    draw.text((30, 155), f"Date         : {current_time}", fill="#666666", font=text_font)
    draw.text((30, 180), "Payment   : CASH (PAID)", fill="#28A745", font=bold_font)

    for x in range(30, width - 30, 10):
        draw.line([(x, 210), (x + 5, 210)], fill="#CCCCCC", width=2)

    draw.rectangle([(30, 225), (width - 30, 260)], fill="#F1F3F5")
    draw.text((40, 242), "ITEM / BRAND", fill="#333333", font=bold_font, anchor="lm")
    draw.text((240, 242), "SIZE", fill="#333333", font=bold_font, anchor="lm")
    draw.text((310, 242), "QTY", fill="#333333", font=bold_font, anchor="lm")
    draw.text((380, 242), "PRICE", fill="#333333", font=bold_font, anchor="lm")

    draw.text((40, 285), str(art_no)[:18], fill="#222222", font=text_font, anchor="lm")
    draw.text((240, 285), str(size), fill="#222222", font=text_font, anchor="lm")
    draw.text((310, 285), str(qty), fill="#222222", font=text_font, anchor="lm")
    draw.text((380, 285), f"₹{price:,.2f}", fill="#222222", font=text_font, anchor="lm")

    for x in range(30, width - 30, 10):
        draw.line([(x, 320), (x + 5, 320)], fill="#CCCCCC", width=2)

    draw.rectangle([(30, 340), (width - 30, 400)], fill="#FFF5F5", outline="#C82333", width=2)
    draw.text((50, 370), "TOTAL AMOUNT PAID", fill="#333333", font=bold_font, anchor="lm")
    draw.text((width - 50, 370), f"₹{total_amount:,.2f}", fill="#C82333", font=title_font, anchor="rm")

    for x in range(30, width - 30, 10):
        draw.line([(x, 430), (x + 5, 430)], fill="#CCCCCC", width=2)

    draw.text((width // 2, 470), "Thank you for shopping with us!", fill="#333333", font=bold_font, anchor="mm")
    draw.text((width // 2, 500), "FAYAS FOOTWEAR • MAIN BAZAAR", fill="#555555", font=text_font, anchor="mm")
    draw.text((width // 2, 530), "Exchange valid within 7 days with this digital bill receipt", fill="#888888", font=small_font, anchor="mm")

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

def generate_link_qr(url_link):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=8, border=2)
    qr.add_data(url_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#C82333", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

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

nav_options = ["📦 Live Stock", "🔥 Fast Selling Products", "📊 Sales Analytics"]

if st.session_state["logged_in"]:
    nav_options = [
        "📦 Live Stock", 
        "🔥 Fast Selling Products",
        "❄️ Dead Stock Finder", 
        "📊 Sales Analytics", 
        "➕ Quick Sale Entry", 
        "📝 Stock Update / New Entry"
    ]

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
                    filtered_df["art_no"].astype(str).str.contains(search_art, case=False, na=False) | 
                    filtered_df["product"].astype(str).str.contains(search_art, case=False, na=False)
                ]
            if gender_filter != "All" and "gender" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["gender"] == gender_filter]
                
            cols_to_show = [c for c in ["product", "gender", "art_no", "size", "quantity", "price"] if c in filtered_df.columns]
            st.dataframe(
                filtered_df[cols_to_show],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No stock data found.")
    except Exception as e:
        st.error(f"Error fetching stock: {e}")

# --- 2. FAST SELLING PRODUCTS PAGE ---
elif choice == "🔥 Fast Selling Products":
    st.subheader("🏆 Top Selling Products (Big to Small)")
    st.caption("Products sorted by total quantity sold (highest demand first).")
    
    try:
        sales_res = supabase.table("sales").select("*").execute()
        stock_res = supabase.table("stock").select("*").execute()
        
        if sales_res.data:
            sdf = pd.DataFrame(sales_res.data)
            stdf = pd.DataFrame(stock_res.data) if stock_res.data else pd.DataFrame()
            
            art_to_product = {}
            if not stdf.empty:
                for _, row in stdf.iterrows():
                    art_to_product[str(row["art_no"]).lower().strip()] = str(row["product"]).strip()
            
            def get_combined_name(art):
                art_str = str(art).strip()
                prod = art_to_product.get(art_str.lower(), "")
                if prod and prod.lower() not in art_str.lower():
                    return f"{prod} {art_str}"
                return art_str

            sdf["product_full_name"] = sdf["art_no"].apply(get_combined_name)
            sdf["total"] = sdf["quantity"] * sdf["price"]
            
            top_selling_df = sdf.groupby("product_full_name").agg(
                total_pairs_sold=("quantity", "sum"),
                total_revenue=("total", "sum")
            ).reset_index()
            
            top_selling_df = top_selling_df.sort_values(by="total_pairs_sold", ascending=False)
            
            top_selling_df = top_selling_df.rename(columns={
                "product_full_name": "Product & Model (Brand - Art No)",
                "total_pairs_sold": "Total Pairs Sold 📦",
                "total_revenue": "Total Revenue (₹) 💰"
            })
            
            st.dataframe(
                top_selling_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            st.subheader("📈 Top Demand Visual Chart")
            chart_data = top_selling_df.set_index("Product & Model (Brand - Art No)")["Total Pairs Sold 📦"]
            st.bar_chart(chart_data)
        else:
            st.info("No sales records available to calculate fast-selling products.")
    except Exception as e:
        st.error(f"Error fetching top selling products: {e}")

# --- 3. DEAD STOCK FINDER PAGE (ADMIN ONLY) ---
elif choice == "❄️ Dead Stock Finder" and st.session_state["logged_in"]:
    st.subheader("❄️ Dead Stock & Capital Lock Finder")
    st.caption("Find products that haven't been sold for days & holding your business capital.")
    
    try:
        stock_res = supabase.table("stock").select("*").execute()
        sales_res = supabase.table("sales").select("*").execute()
        
        stock_data = stock_res.data
        sales_data = sales_res.data
        
        if stock_data:
            stock_df = pd.DataFrame(stock_data)
            sales_df = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()
            
            if "created_at" in stock_df.columns:
                stock_df["stock_added_date"] = pd.to_datetime(stock_df["created_at"]).dt.tz_convert(IST).dt.strftime("%d %b %Y")
            else:
                stock_df["stock_added_date"] = "N/A"

            days_filter = st.slider("Select Inactive Period (Days without sale):", min_value=7, max_value=120, value=30, step=7)
            
            sold_art_numbers = set()
            last_sold_map = {}
            
            if not sales_df.empty:
                sales_df["created_at"] = pd.to_datetime(sales_df["created_at"], utc=True).dt.tz_convert(IST)
                cutoff_date = pd.Timestamp.now(tz=IST) - pd.Timedelta(days=days_filter)
                
                recent_sales = sales_df[sales_df["created_at"] >= cutoff_date]
                sold_art_numbers = set(recent_sales["art_no"].astype(str).str.lower().unique())
                
                for art, group in sales_df.groupby(sales_df["art_no"].astype(str).str.lower()):
                    latest_date = group["created_at"].max()
                    last_sold_map[art] = latest_date.strftime("%d %b %Y")
            
            stock_df["art_no_clean"] = stock_df["art_no"].astype(str).str.lower()
            dead_stock_df = stock_df[~stock_df["art_no_clean"].isin(sold_art_numbers) & (stock_df["quantity"] > 0)].copy()
            
            if not dead_stock_df.empty:
                dead_stock_df["last_sold_date"] = dead_stock_df["art_no_clean"].map(last_sold_map).fillna("Never Sold")
                dead_stock_df["locked_amount"] = dead_stock_df["quantity"] * dead_stock_df["price"]
                total_locked_capital = dead_stock_df["locked_amount"].sum()
                total_dead_pairs = dead_stock_df["quantity"].sum()
                
                m1, m2 = st.columns(2)
                m1.metric("🔴 Dead Stock Pairs", f"{total_dead_pairs} Pairs")
                m2.metric("💰 Locked Capital Amount", f"₹ {total_locked_capital:,.2f}")
                
                st.warning(f"⚠️ {len(dead_stock_df)} stock entries have **ZERO sales** in the last {days_filter} days!")
                
                show_cols = [c for c in [
                    "product", "gender", "art_no", "size", "quantity", 
                    "price", "locked_amount", "stock_added_date", "last_sold_date"
                ] if c in dead_stock_df.columns]
                
                st.dataframe(
                    dead_stock_df[show_cols],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success(f"🎉 Great job! No dead stock found for the last {days_filter} days.")
        else:
            st.info("No stock data available.")
    except Exception as e:
        st.error(f"Error analyzing dead stock: {e}")

# --- 4. QUICK SALE ENTRY ---
elif choice == "➕ Quick Sale Entry" and st.session_state["logged_in"]:
    st.subheader("➕ Quick Sale Entry")
    
    try:
        stock_data = supabase.table("stock").select("*").execute().data
        stock_df = pd.DataFrame(stock_data) if stock_data else pd.DataFrame()
    except Exception as e:
        stock_df = pd.DataFrame()

    if not stock_df.empty:
        db_stock_options = [
            f"{row.get('product', '')} | Gender:{row.get('gender', 'N/A')} | Art:{row.get('art_no', '')} | Size:{row.get('size', '')} | MRP: ₹{row.get('price', 0)} | Stock:{row.get('quantity', 0)} pairs" 
            for _, row in stock_df.iterrows()
        ]
        
        def on_stock_select():
            selected = st.session_state["search_stock_item"]
            if selected:
                idx = db_stock_options.index(selected)
                row = stock_df.iloc[idx]
                st.session_state["sale_art"] = f"{row.get('product', '')} {row.get('art_no', '')}".strip()
                st.session_state["sale_gender"] = str(row.get("gender", "Gents"))
                st.session_state["sale_size"] = str(row.get("size", ""))
                st.session_state["sale_price"] = float(row.get("price", 0.0))

        st.selectbox(
            "🔍 Search Database Stock:",
            options=db_stock_options,
            index=None,
            placeholder="Type brand name, art no or gender here...",
            key="search_stock_item",
            on_change=on_stock_select
        )
    else:
        st.info("No stock available in database inventory.")

    st.divider()

    art_no = st.text_input("Art No / Brand", key="sale_art")
    gender = st.selectbox("Gender Category", ["Gents", "Ladies", "Kids"], key="sale_gender")
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
                        item_gender = str(item.get("gender", "")).lower()
                        if item_gender and item_gender != gender.lower():
                            continue

                        if (art_no.lower() in str(item.get("art_no", "")).lower()) or \
                           (art_no.lower() in str(item.get("product", "")).lower()) or \
                           (str(item.get("product", "")).lower() in art_no.lower()):
                            matched_item = item
                            break
                
                if not matched_item:
                    show_error_popup(f"❌ Cannot record sale!\n\nThis item ({gender}, Size: {size}) is NOT FOUND in stock inventory.")
                elif matched_item["quantity"] < qty:
                    show_error_popup(f"⚠️ Insufficient Stock!\n\nAvailable Stock: {matched_item['quantity']} pairs\nRequested Quantity: {qty} pairs")
                else:
                    supabase.table("sales").insert({
                        "art_no": art_no, "gender": gender, "size": size, "quantity": qty, "price": price
                    }).execute()
                    
                    current_qty = matched_item["quantity"]
                    new_qty = current_qty - qty
                    supabase.table("stock").update({"quantity": new_qty}).eq("id", matched_item["id"]).execute()
                    
                    st.success(f"✅ Sale Recorded! Stock updated from {current_qty} to {new_qty} pairs.")
                    
                    if record_and_bill:
                        # Bill No created using exact IST time
                        bill_no = f"FFW-{datetime.now(IST).strftime('%Y%m%d%H%M%S')}"
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

# --- 5. STOCK UPDATE / NEW ENTRY ---
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

# --- 6. SALES ANALYTICS PAGE ---
elif choice == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics & History")
    try:
        sales_res = supabase.table("sales").select("*").order("created_at", desc=True).execute()
        stock_res = supabase.table("stock").select("*").execute()

        if sales_res.data:
            sdf = pd.DataFrame(sales_res.data)
            stdf = pd.DataFrame(stock_res.data) if stock_res.data else pd.DataFrame()
            
            art_to_product = {}
            if not stdf.empty:
                for _, row in stdf.iterrows():
                    art_to_product[str(row["art_no"]).lower().strip()] = str(row["product"]).strip()

            def extract_product_and_art(art_val):
                art_str = str(art_val).strip()
                parts = art_str.split(" ", 1)
                if len(parts) > 1 and not parts[0].isdigit():
                    return parts[0].title(), parts[1]
                
                found_prod = art_to_product.get(art_str.lower(), "")
                if found_prod:
                    return found_prod.title(), art_str
                
                if not art_str.isdigit():
                    return art_str.title(), "-"
                
                return "Footwear", art_str

            sdf[["product", "clean_art_no"]] = sdf["art_no"].apply(lambda x: pd.Series(extract_product_and_art(x)))
            
            # --- CONVERT UTC TIMESTAMP TO INDIA TIME (IST) FOR TABLE DISPLAY ---
            sdf["formatted_time"] = pd.to_datetime(sdf["created_at"], utc=True).dt.tz_convert(IST).dt.strftime("%d %b %Y, %I:%M %p")
            sdf["sno"] = range(1, len(sdf) + 1)
            sdf["total"] = sdf["quantity"] * sdf["price"]
            
            total_rev = sdf['total'].sum()
            total_pairs_sold = sdf['quantity'].sum()
            
            m1, m2 = st.columns(2)
            m1.metric("💰 Total Sales Revenue", f"₹ {total_rev:,.2f}")
            m2.metric("📦 Total Pairs Sold", f"{total_pairs_sold} Pairs")
            
            st.divider()
            st.subheader("📜 Detailed Sales Log History")
            
            display_sales_df = sdf[[
                "sno", "product", "clean_art_no", "size", "quantity", "price", "formatted_time"
            ]].rename(columns={
                "sno": "sno",
                "product": "product",
                "clean_art_no": "art no",
                "size": "size",
                "quantity": "quantity",
                "price": "price",
                "formatted_time": "sales data&time"
            })
            
            st.dataframe(
                display_sales_df,
                use_container_width=True,
                hide_index=True
            )
            
            if st.session_state["logged_in"]:
                st.divider()
                st.subheader("🔄 Edit Sale / Customer Return Handle")
                
                sale_options = {
                    f"ID: {row['id']} | Product: {row['product']} | Art: {row['clean_art_no']} | Size: {row['size']} | Qty: {row['quantity']} | Price: ₹{row['price']}": row
                    for _, row in sdf.iterrows()
                }
                
                selected_sale_label = st.selectbox("Select Sale Entry to Edit / Return:", list(sale_options.keys()))
                selected_sale = sale_options[selected_sale_label]
                
                with st.form("edit_sale_form"):
                    st.markdown(f"**Editing Sale Record (ID: {selected_sale['id']})**")
                    edit_art = st.text_input("Art No / Brand", value=str(selected_sale["art_no"]))
                    
                    default_gen_idx = 0
                    if "gender" in selected_sale and selected_sale["gender"] in ["Gents", "Ladies", "Kids"]:
                        default_gen_idx = ["Gents", "Ladies", "Kids"].index(selected_sale["gender"])
                    
                    edit_gender = st.selectbox("Gender Category", ["Gents", "Ladies", "Kids"], index=default_gen_idx)
                    edit_size = st.text_input("Size", value=str(selected_sale["size"]))
                    edit_qty = st.number_input("Quantity Sold", min_value=0, value=int(selected_sale["quantity"]), step=1)
                    edit_price = st.number_input("Price per Unit (₹)", min_value=0.0, value=float(selected_sale["price"]), step=10.0)
                    
                    form_col1, form_col2 = st.columns(2)
                    update_btn = form_col1.form_submit_button("✏️ Save Changes / Update Sale", type="primary")
                    return_delete_btn = form_col2.form_submit_button("❌ Full Return / Delete Sale", type="secondary")
                    
                    if update_btn:
                        old_qty = int(selected_sale["quantity"])
                        qty_diff = old_qty - edit_qty
                        
                        supabase.table("sales").update({
                            "art_no": edit_art,
                            "gender": edit_gender,
                            "size": edit_size,
                            "quantity": edit_qty,
                            "price": edit_price
                        }).eq("id", selected_sale["id"]).execute()
                        
                        if qty_diff != 0:
                            stock_item = supabase.table("stock").select("*").eq("size", edit_size).execute()
                            if stock_item.data:
                                matched = None
                                for s in stock_item.data:
                                    if edit_art.lower() in str(s.get("art_no", "")).lower() or edit_art.lower() in str(s.get("product", "")).lower():
                                        matched = s
                                        break
                                if matched:
                                    new_stock_qty = matched["quantity"] + qty_diff
                                    supabase.table("stock").update({"quantity": new_stock_qty}).eq("id", matched["id"]).execute()
                        
                        st.success("✅ Sale updated and Stock automatically adjusted!")
                        st.rerun()
                        
                    if return_delete_btn:
                        return_qty = int(selected_sale["quantity"])
                        sale_size = str(selected_sale["size"])
                        sale_art = str(selected_sale["art_no"])
                        
                        supabase.table("sales").delete().eq("id", selected_sale["id"]).execute()
                        
                        stock_item = supabase.table("stock").select("*").eq("size", sale_size).execute()
                        if stock_item.data:
                            matched = None
                            for s in stock_item.data:
                                if sale_art.lower() in str(s.get("art_no", "")).lower() or sale_art.lower() in str(s.get("product", "")).lower():
                                    matched = s
                                    break
                            if matched:
                                restored_qty = matched["quantity"] + return_qty
                                supabase.table("stock").update({"quantity": restored_qty}).eq("id", matched["id"]).execute()
                        
                        st.success(f"🗑️ Sale record deleted and {return_qty} pair(s) restored back to stock!")
                        st.rerun()

        else:
            st.info("No sales recorded yet.")
    except Exception as e:
        st.error(f"Error fetching sales: {e}")
