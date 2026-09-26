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
    page_title="Fayas Footwear - Dashboard",
    page_icon="👞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SECRETS & CLIENT INITIALIZATION ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Secret Configuration Error: Check your Streamlit Secrets! Details: {e}")
    st.stop()


# --- HELPER FUNCTIONS ---
def get_ist_time():
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def generate_qr_code(data_str):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def format_df_dates(df):
    if df.empty:
        return df
    formatted_df = df.copy()
    for col in formatted_df.columns:
        if any(
            keyword in col.lower()
            for keyword in ["created_at", "date", "time", "updated_at", "timestamp"]
        ):
            try:
                converted_series = pd.to_datetime(formatted_df[col], utc=True)
                formatted_df[col] = (
                    converted_series.dt.tz_convert("Asia/Kolkata").dt.strftime(
                        "%d/%m/%Y %I:%M %p"
                    )
                )
            except Exception:
                try:
                    formatted_df[col] = pd.to_datetime(
                        formatted_df[col]
                    ).dt.strftime("%d/%m/%Y %I:%M %p")
                except Exception:
                    pass
    return formatted_df


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
menu_options = [
    "📦 Live Stock",
    "📊 Sales Analytics",
    "🎯 Product Insights(FLD Stocks)",
]

if st.session_state["admin_logged_in"]:
    menu_options.extend([
        "➕ Quick Sale Entry",
        "📝 Stock Update / New Entry",
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
            st.warning("No stock data found in Supabase database.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                gender_opts = df_stock["gender"].dropna().unique()
                gender_filter = st.multiselect(
                    "Gender Category",
                    options=gender_opts,
                    default=[],
                    placeholder="Select Gender...",
                )
            with col2:
                brand_opts = df_stock["product_name"].dropna().unique()
                brand_filter = st.multiselect(
                    "Brand / Product",
                    options=brand_opts,
                    default=[],
                    placeholder="Select Brand...",
                )
            with col3:
                search_art = st.text_input("Search Art No", "")

            filtered_df = df_stock.copy()
            if gender_filter:
                filtered_df = filtered_df[filtered_df["gender"].isin(gender_filter)]
            if brand_filter:
                filtered_df = filtered_df[filtered_df["product_name"].isin(brand_filter)]
            if search_art:
                filtered_df = filtered_df[
                    filtered_df["art_no"].astype(str).str.contains(search_art, case=False, na=False)
                ]

            if st.session_state.get("admin_logged_in", False):
                filtered_df.insert(0, "Select", False)

                edited_df = st.data_editor(
                    filtered_df,
                    key="stock_editor",
                    num_rows="dynamic",
                    disabled=["id", "created_at"],
                    use_container_width=True,
                )

                col_b1, col_b2 = st.columns([1, 1])

                with col_b1:
                    if st.button("💾 Save Changes", type="primary"):
                        try:
                            for index, row in edited_df.iterrows():
                                row_id = row.get("id")
                                if pd.notnull(row_id):
                                    update_payload = {
                                        "product_name": str(row["product_name"]),
                                        "gender": str(row["gender"]),
                                        "art_no": str(row["art_no"]),
                                        "size": str(row["size"]),
                                        "qty": int(row["qty"]),
                                        "mrp_og": float(row.get("mrp_og", 0.0)),
                                        "wp": float(row.get("wp", 0.0)),
                                        "mrp_d": float(row.get("mrp_d", 0.0)),
                                    }
                                    supabase.table("stock").update(update_payload).eq("id", row_id).execute()
                            st.success("✅ Stock details updated successfully in Supabase!")
                            st.rerun()
                        except Exception as save_err:
                            st.error(f"Error saving changes: {save_err}")

                with col_b2:
                    if st.button("🗑️ Delete Selected Items", type="secondary"):
                        to_delete_df = edited_df[edited_df["Select"] == True]

                        if to_delete_df.empty:
                            st.warning("⚠️ No items selected! Please tick the 'Select' box first.")
                        else:
                            try:
                                delete_count = 0
                                for index, row in to_delete_df.iterrows():
                                    row_id = row.get("id")
                                    if pd.notnull(row_id):
                                        supabase.table("stock").delete().eq("id", row_id).execute()
                                        delete_count += 1
                                st.success(f"🗑️ Successfully deleted {delete_count} items from database!")
                                st.rerun()
                            except Exception as delete_err:
                                st.error(f"Error deleting items: {delete_err}")
            else:
                formatted_view = format_df_dates(filtered_df)
                st.dataframe(formatted_view, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching stock: {e}")

# ---------------------------------------------------------
# 2. SALES ANALYTICS (WITH DELETE & AUTO RESTOCK)
# ---------------------------------------------------------
elif menu == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics & Profitability")
    try:
        sales_res = supabase.table("sales").select("*").execute()
        df_sales = pd.DataFrame(sales_res.data)

        if df_sales.empty:
            st.info("No sales data recorded yet.")
        else:
            df_sales["datetime_ist"] = pd.to_datetime(df_sales["created_at"]).dt.tz_convert("Asia/Kolkata")
            df_sales["date_only"] = df_sales["datetime_ist"].dt.date

            today_date = get_ist_time().date()

            view_type = st.radio(
                "Select Sales View:",
                ["🔥 Today's Live Sales", "📜 History Sales (By Date)"],
                horizontal=True,
            )

            if view_type == "🔥 Today's Live Sales":
                st.write(f"### 🗓️ Today's Sales ({today_date.strftime('%d/%m/%Y')})")
                df_filtered = df_sales[df_sales["date_only"] == today_date].copy()
            else:
                st.write("### 📜 Sales History")
                selected_date = st.date_input(
                    "Select Date for History",
                    value=today_date - timedelta(days=1),
                )
                df_filtered = df_sales[df_sales["date_only"] == selected_date].copy()

            if df_filtered.empty:
                st.warning("No sales recorded for this date.")
            else:
                df_filtered["revenue"] = df_filtered["qty"] * df_filtered["price"]
                df_filtered["cost"] = df_filtered["qty"] * df_filtered.get("wp", 0.0)
                df_filtered["profit"] = df_filtered["revenue"] - df_filtered["cost"]

                total_qty = df_filtered["qty"].sum()
                total_rev = df_filtered["revenue"].sum()
                total_profit = df_filtered["profit"].sum()

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Pair Sales", f"{total_qty} Pairs")
                m2.metric("Total Revenue", f"₹{total_rev:,.2f}")
                m3.metric("Estimated Profit", f"₹{total_profit:,.2f}")

                df_filtered = format_df_dates(df_filtered)
                display_cols = [c for c in df_filtered.columns if c not in ["datetime_ist", "date_only", "cost", "profit"]]
                df_display = df_filtered[display_cols].sort_values(by="id", ascending=False)

                if st.session_state.get("admin_logged_in", False):
                    df_display.insert(0, "Select", False)

                    edited_sales_df = st.data_editor(
                        df_display,
                        key="sales_editor",
                        disabled=[c for c in display_cols if c != "Select"],
                        use_container_width=True,
                    )

                    if st.button("🗑️ Delete Selected Sales Record(s)", type="secondary"):
                        to_delete_sales = edited_sales_df[edited_sales_df["Select"] == True]

                        if to_delete_sales.empty:
                            st.warning("⚠️ Please select at least one sales record to delete!")
                        else:
                            try:
                                delete_count = 0
                                for index, row in to_delete_sales.iterrows():
                                    sale_id = row.get("id")
                                    if pd.notnull(sale_id):
                                        p_name = str(row["product_name"])
                                        g_name = str(row["gender"])
                                        a_no = str(row["art_no"])
                                        s_size = str(row["size"])
                                        s_qty = int(row["qty"])

                                        stock_match = supabase.table("stock").select("*").eq("product_name", p_name).eq("gender", g_name).eq("art_no", a_no).eq("size", s_size).execute()
                                        if stock_match.data:
                                            stk_item = stock_match.data[0]
                                            restocked_qty = int(stk_item.get("qty", 0)) + s_qty
                                            supabase.table("stock").update({"qty": restocked_qty}).eq("id", stk_item["id"]).execute()

                                        supabase.table("sales").delete().eq("id", sale_id).execute()
                                        delete_count += 1

                                st.success(f"🗑️ Successfully deleted {delete_count} sale entry(s) and restocked quantity back to inventory!")
                                st.rerun()
                            except Exception as del_sales_err:
                                st.error(f"Error deleting sales record: {del_sales_err}")
                else:
                    st.dataframe(df_display, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

# ---------------------------------------------------------
# 3. PRODUCT INSIGHTS
# ---------------------------------------------------------
elif menu == "🎯 Product Insights(FLD Stocks)":
    st.subheader("🎯 Product Insights")

    tab1, tab2, tab3 = st.tabs([
        "🔥 Top / Fast Selling Products",
        "⚠️ Dead Stock (Zero Sales)",
        "📉 Low Stock Alert (≤ 2 Pairs)",
    ])

    with tab1:
        try:
            sales_res = supabase.table("sales").select("*").execute()
            df_sales = pd.DataFrame(sales_res.data)

            if df_sales.empty:
                st.info("No sales data available yet.")
            else:
                group_cols = ["product_name", "gender", "art_no", "size"]
                fast_selling = df_sales.groupby(group_cols)["qty"].sum().reset_index()
                fast_selling = fast_selling.sort_values(by="qty", ascending=False)
                st.dataframe(fast_selling, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading fast selling products: {e}")

    with tab2:
        try:
            stock_res = supabase.table("stock").select("*").execute()
            sales_res = supabase.table("sales").select("*").execute()

            df_stock = pd.DataFrame(stock_res.data)
            df_sales = pd.DataFrame(sales_res.data)

            if df_stock.empty:
                st.info("Stock inventory is empty.")
            else:
                if not df_sales.empty:
                    merge_cols = ["product_name", "gender", "art_no", "size"]
                    sold_items = df_sales[merge_cols].drop_duplicates()
                    dead_stock = pd.merge(
                        df_stock,
                        sold_items,
                        on=merge_cols,
                        how="left",
                        indicator=True,
                    )
                    dead_stock = dead_stock[dead_stock["_merge"] == "left_only"].drop(columns=["_merge"])
                else:
                    dead_stock = df_stock

                st.warning(f"Found {len(dead_stock)} stock items with zero sales record:")
                dead_stock_formatted = format_df_dates(dead_stock)
                st.dataframe(dead_stock_formatted, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading dead stock: {e}")

    with tab3:
        try:
            stock_res = supabase.table("stock").select("*").execute()
            df_stock = pd.DataFrame(stock_res.data)

            if df_stock.empty:
                st.info("Stock inventory is empty.")
            else:
                low_stock = df_stock[df_stock["qty"] <= 2].sort_values(by="qty", ascending=True)

                if low_stock.empty:
                    st.success("🎉 All items have sufficient stock (more than 2 pairs)!")
                else:
                    st.error(f"🚨 Found {len(low_stock)} items with low stock (2 pairs or less):")
                    low_stock_formatted = format_df_dates(low_stock)
                    st.dataframe(low_stock_formatted, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading low stock: {e}")

# ---------------------------------------------------------
# 4. QUICK SALE ENTRY
# ---------------------------------------------------------
elif menu == "➕ Quick Sale Entry" and st.session_state["admin_logged_in"]:
    st.subheader("Quick Sale Entry")

    components.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const inputs = Array.from(doc.querySelectorAll('input[type="text"], input[role="combobox"], input[type="number"]'));
                const activeEl = doc.activeElement;
                const index = inputs.indexOf(activeEl);
                if (index > -1 && index < inputs.length - 1) {
                    inputs[index + 1].focus();
                    e.preventDefault();
                }
            }
        });
        </script>
        """,
        height=0,
    )

    try:
        stock_res = supabase.table("stock").select("*").execute()
        df_stock = pd.DataFrame(stock_res.data)

        if df_stock.empty:
            st.error("No stock available in database! Please add stock first.")
        else:
            products_list = list(df_stock["product_name"].dropna().unique())
            selected_product = st.selectbox(
                "Product",
                options=products_list,
                index=None,
                placeholder="Select Product...",
                key="sb_product",
            )

            sub_1 = pd.DataFrame()
            gender_list = []
            if selected_product:
                sub_1 = df_stock[df_stock["product_name"] == selected_product]
                gender_list = list(sub_1["gender"].dropna().unique())

            selected_gender = st.selectbox(
                "Gender",
                options=gender_list,
                index=None,
                placeholder="Select Gender...",
                key="sb_gender",
            )

            sub_2 = pd.DataFrame()
            art_list = []
            if selected_product and selected_gender and not sub_1.empty:
                sub_2 = sub_1[sub_1["gender"] == selected_gender]
                art_list = list(sub_2["art_no"].dropna().unique())

            selected_art_no = st.selectbox(
                "Art No",
                options=art_list,
                index=None,
                placeholder="Select Art No...",
                key="sb_art_no",
            )

            sub_3 = pd.DataFrame()
            size_list = []
            if selected_product and selected_gender and selected_art_no and not sub_2.empty:
                sub_3 = sub_2[sub_2["art_no"] == selected_art_no]
                size_list = list(sub_3["size"].dropna().unique())

            selected_size = st.selectbox(
                "Size",
                options=size_list,
                index=None,
                placeholder="Select Size...",
                key="sb_size",
            )

            available_qty = 0
            mrp_og_val = 0.0
            wp_val = 0.0
            mrp_d_val = 0.0
            selected_item = None

            if selected_product and selected_gender and selected_art_no and selected_size and not sub_3.empty:
                matched_rows = sub_3[sub_3["size"] == selected_size]
                if not matched_rows.empty:
                    selected_item = matched_rows.iloc[0]
                    available_qty = selected_item.get("qty", 0)
                    mrp_og_val = float(selected_item.get("mrp_og", 0.0))
                    wp_val = float(selected_item.get("wp", 0.0))
                    mrp_d_val = float(selected_item.get("mrp_d", 0.0))

                    st.info(f"Available Qty: **{available_qty}** | Original MRP: **₹{mrp_og_val}** | Wholesale Price (WP): **₹{wp_val}** | Duplicate MRP (MRP D): **₹{mrp_d_val}**")

            with st.form("exact_quick_sale_form"):
                col_qty, col_price, col_pay = st.columns(3)

                with col_qty:
                    sell_qty = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=max(1, int(available_qty)),
                        value=1,
                        key="num_qty",
                    )

                with col_price:
                    selling_price = st.number_input(
                        "Selling Price (MRP D)",
                        min_value=0.0,
                        value=mrp_d_val,
                        key="num_price",
                    )

                with col_pay:
                    payment_mode = st.radio("Payment", options=["Cash", "UPI"], horizontal=True)

                sale_date = st.date_input("Sale Date", value=get_ist_time().date())

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submit_sale = st.form_submit_button("Sale")
                with col_btn2:
                    generate_qr_btn = st.form_submit_button("Generate QR")

            if submit_sale or generate_qr_btn:
                if not (selected_product and selected_gender and selected_art_no and selected_size):
                    st.error("Please select Product, Gender, Art No, and Size first!")
                elif selected_item is None:
                    st.error("Selected item not found in stock!")
                else:
                    now_time = get_ist_time().time()
                    custom_datetime = (
                        datetime.combine(sale_date, now_time)
                        .replace(tzinfo=ZoneInfo("Asia/Kolkata"))
                        .isoformat()
                    )

                    sale_data = {
                        "product_name": selected_product,
                        "gender": selected_gender,
                        "art_no": selected_art_no,
                        "size": str(selected_size),
                        "qty": int(sell_qty),
                        "mrp_og": mrp_og_val,
                        "wp": wp_val,
                        "price": float(selling_price),
                        "payment_mode": payment_mode,
                        "created_at": custom_datetime,
                    }

                    if submit_sale:
                        supabase.table("sales").insert(sale_data).execute()

                        new_qty = max(0, int(available_qty) - int(sell_qty))
                        supabase.table("stock").update({"qty": new_qty}).eq("id", selected_item["id"]).execute()

                        st.success(f"Sale Recorded ({payment_mode}) & Stock Deducted Successfully!")

                    if generate_qr_btn or submit_sale:
                        bill_details = (
                            f"FAYAS FOOTWEAR\nDate: {sale_date.strftime('%d/%m/%Y')}\n"
                            f"Item: {selected_product} ({selected_gender})\n"
                            f"Art: {selected_art_no} | Size: {selected_size}\n"
                            f"Qty: {sell_qty} x ₹{selling_price}\n"
                            f"Total: ₹{sell_qty * selling_price}\n"
                            f"Payment: {payment_mode}"
                        )
                        qr_img = generate_qr_code(bill_details)

                        st.write("### 🧾 Digital Receipt")
                        st.text(bill_details)
                        st.image(qr_img, caption="Scan QR for Digital Bill Receipt")

    except Exception as e:
        st.error(f"Error during quick sale: {e}")

# ---------------------------------------------------------
# 5. STOCK UPDATE / NEW ENTRY (MANUAL & BULK EXCEL IMPORT)
# ---------------------------------------------------------
elif menu == "📝 Stock Update / New Entry" and st.session_state["admin_logged_in"]:
    st.subheader("📝 Stock Update & Bulk Excel Import")

    tab_manual, tab_excel = st.tabs(["✍️ Single Manual Entry", "📁 Bulk Excel / CSV Import"])

    # --- TAB 1: SINGLE MANUAL ENTRY ---
    with tab_manual:
        with st.form("manual_stock_form"):
            col1, col2 = st.columns(2)
            with col1:
                product_name = st.text_input("Brand / Product Name (e.g., Walkaroo)")
                gender = st.selectbox("Gender", ["Gents", "Ladies", "Kids (B)", "Kids (G)"])
                art_no = st.text_input("Art No (e.g., W-102)")
                size = st.text_input("Size (e.g., 7 or 8)")
            with col2:
                qty = st.number_input("Quantity", min_value=1, value=12)
                mrp_og = st.number_input("Original MRP (mrp_og)", min_value=0.0, value=500.0)
                wp = st.number_input("Wholesale Price (wp)", min_value=0.0, value=250.0)
                mrp_d = st.number_input("Duplicate MRP (mrp_d)", min_value=0.0, value=350.0)

            submit_stock = st.form_submit_button("💾 Save / Update Stock")

            if submit_stock:
                if not product_name or not art_no or not size:
                    st.error("Please fill all required fields!")
                else:
                    try:
                        all_stock = supabase.table("stock").select("*").execute()
                        df_all = pd.DataFrame(all_stock.data) if all_stock.data else pd.DataFrame()

                        existing = pd.DataFrame()
                        if not df_all.empty:
                            existing = df_all[
                                (df_all["product_name"].astype(str).str.lower() == product_name.strip().lower())
                                & (df_all["gender"].astype(str).str.lower() == gender.strip().lower())
                                & (df_all["art_no"].astype(str).str.lower() == art_no.strip().lower())
                                & (df_all["size"].astype(str) == str(size).strip())
                            ]

                        if not existing.empty:
                            existing_row = existing.iloc[0]
                            updated_qty = int(existing_row["qty"]) + int(qty)
                            supabase.table("stock").update({
                                "qty": updated_qty,
                                "mrp_og": float(mrp_og),
                                "wp": float(wp),
                                "mrp_d": float(mrp_d),
                            }).eq("id", existing_row["id"]).execute()
                            st.success(f"Stock Updated! Added {qty} pairs to existing item. Total: {updated_qty}")
                        else:
                            payload = {
                                "product_name": product_name.strip(),
                                "gender": gender,
                                "art_no": art_no.strip(),
                                "size": str(size).strip(),
                                "qty": int(qty),
                                "mrp_og": float(mrp_og),
                                "wp": float(wp),
                                "mrp_d": float(mrp_d),
                                "created_at": get_ist_time().isoformat(),
                            }
                            supabase.table("stock").insert(payload).execute()
                            st.success("New Stock Item Created Successfully!")
                    except Exception as e:
                        st.error(f"Failed to add stock: {e}")

# --- TAB 2: BULK EXCEL / CSV IMPORT WITH PREVIEW & EDIT ---
    with tab_excel:
        st.write("### 📤 Upload Excel or CSV File")
        uploaded_file = st.file_uploader("Choose an Excel or CSV file", type=["xlsx", "csv"])

        if uploaded_file is not None:
            try:
                # 1. Read file raw
                if uploaded_file.name.endswith(".csv"):
                    df_raw = pd.read_csv(uploaded_file, header=None)
                else:
                    df_raw = pd.read_excel(uploaded_file, header=None)

                # 2. Smart header row detection
                header_idx = 0
                for idx, row in df_raw.iterrows():
                    row_str = " ".join(row.dropna().astype(str)).lower()
                    if "product" in row_str or "art" in row_str:
                        header_idx = idx
                        break

                # 3. Reload DataFrame with correct header row
                if uploaded_file.name.endswith(".csv"):
                    df_upload = pd.read_csv(uploaded_file, skiprows=header_idx)
                else:
                    df_upload = pd.read_excel(uploaded_file, skiprows=header_idx)

                # Clean header column names
                df_upload.columns = [str(col).strip().lower().replace("-", "_").replace(".", "_") for col in df_upload.columns]

                # Map column names
                col_mapping = {
                    's_no': 's_no', 'sno': 's_no', 's__no': 's_no',
                    'product_name': 'product_name', 'productname': 'product_name', 'product': 'product_name',
                    'gender': 'gender',
                    'art_no': 'art_no', 'artno': 'art_no', 'art': 'art_no',
                    'size': 'size',
                    'qty': 'qty', 'quantity': 'qty',
                    'mrp': 'mrp_og', 'mrp_og': 'mrp_og', 'original_mrp': 'mrp_og',
                    'w_p': 'wp', 'wp': 'wp', 'wholesale': 'wp', 'wholesale_price': 'wp',
                    'duplicate_mrp': 'mrp_d', 'mrp_d': 'mrp_d'
                }
                
                renamed_cols = {}
                for col in df_upload.columns:
                    clean_c = str(col).strip()
                    renamed_cols[col] = col_mapping.get(clean_c, clean_c)
                df_upload.rename(columns=renamed_cols, inplace=True)

                # --- 🔴 COMPLETE REMOVAL OF S_NO COLUMN & TOTAL ROWS ---
                if "s_no" in df_upload.columns:
                    df_upload.drop(columns=["s_no"], inplace=True)

                if "product_name" in df_upload.columns:
                    df_upload = df_upload[
                        ~df_upload["product_name"].astype(str).str.lower().str.strip().isin(["total", "sum", "grand total", "none", "nan", ""])
                    ]

                # Add explicit check-box column for row deletion
                if "Delete_Row" not in df_upload.columns:
                    df_upload.insert(0, "Delete_Row", False)

                # Session State Storage
                if "edited_df" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
                    st.session_state.edited_df = df_upload
                    st.session_state.file_name = uploaded_file.name

                st.write("### 🔍 Cleaned Preview & Edit")
                st.caption("💡 **s_no column ni poorthiga delete chesam.** Row-ni remove cheyaniki `Delete_Row` box check chesi keela unna button press cheyandi!")

                # Render Data Table without s_no column
                updated_df = st.data_editor(
                    st.session_state.edited_df,
                    column_config={
                        "Delete_Row": st.column_config.CheckboxColumn(
                            "Delete?",
                            help="Row ni delete cheyaniki tick cheyandi",
                            default=False
                        )
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    key="data_editor_key"
                )

                # Delete Rows Action Button
                col_btn, _ = st.columns([1, 2])
                with col_btn:
                    if st.button("🗑️ Selected Rows-a Delete Pannu", type="secondary"):
                        filtered_df = updated_df[updated_df["Delete_Row"] == False]
                        st.session_state.edited_df = filtered_df
                        st.success("Selected rows removed successfully!")
                        st.rerun()

                st.divider()

                # Upload to Supabase Action Button
                if st.button("🚀 Upload & Sync All to Database", type="primary"):
                    final_upload_df = updated_df[updated_df["Delete_Row"] == False]
                    
                    if final_upload_df.empty:
                        st.warning("Table kaaliyaa irukku!")
                    else:
                        all_stock = supabase.table("stock").select("*").execute()
                        df_all = pd.DataFrame(all_stock.data) if all_stock.data else pd.DataFrame()

                        success_count = 0
                        error_count = 0

                        for idx, row in final_upload_df.iterrows():
                            try:
                                p_name = str(row.get("product_name", "")).strip()
                                
                                if not p_name or p_name.lower() in ["total", "nan", "none", "grand total", "sum", ""]:
                                    continue

                                g_raw = str(row.get("gender", "")).strip().lower()
                                
                                if g_raw in ['g', 'gents', 'm', 'male']:
                                    g_name = "Gents"
                                elif g_raw in ['l', 'ladies', 'f', 'female']:
                                    g_name = "Ladies"
                                elif g_raw in ['kb', 'kids b', 'kids (b)']:
                                    g_name = "Kids (B)"
                                elif g_raw in ['kg', 'kids g', 'kids (g)']:
                                    g_name = "Kids (G)"
                                else:
                                    g_name = g_raw.capitalize() if g_raw and g_raw != "nan" else "Gents"

                                a_no = str(row.get("art_no", "")).strip()
                                s_size = str(row.get("size", "")).strip()
                                
                                if not a_no or a_no.lower() in ["nan", "none", ""]:
                                    continue

                                try:
                                    q_val = int(float(row.get("qty", 1)))
                                except:
                                    q_val = 1
                                    
                                try:
                                    m_og = float(row.get("mrp_og", 0.0))
                                except:
                                    m_og = 0.0
                                    
                                try:
                                    w_val = float(row.get("wp", 0.0))
                                except:
                                    w_val = 0.0
                                    
                                try:
                                    m_d = float(row.get("mrp_d", 0.0)) if pd.notnull(row.get("mrp_d")) else m_og
                                except:
                                    m_d = m_og

                                # Check Duplicate/Existing Entry
                                existing = pd.DataFrame()
                                if not df_all.empty:
                                    existing = df_all[
                                        (df_all["product_name"].astype(str).str.lower() == p_name.lower())
                                        & (df_all["gender"].astype(str).str.lower() == g_name.lower())
                                        & (df_all["art_no"].astype(str).str.lower() == a_no.lower())
                                        & (df_all["size"].astype(str) == s_size)
                                    ]

                                if not existing.empty:
                                    existing_row = existing.iloc[0]
                                    updated_qty = int(existing_row["qty"]) + q_val
                                    supabase.table("stock").update({
                                        "qty": updated_qty,
                                        "mrp_og": m_og,
                                        "wp": w_val,
                                        "mrp_d": m_d,
                                    }).eq("id", existing_row["id"]).execute()
                                else:
                                    payload = {
                                        "product_name": p_name,
                                        "gender": g_name,
                                        "art_no": a_no,
                                        "size": s_size,
                                        "qty": q_val,
                                        "mrp_og": m_og,
                                        "wp": w_val,
                                        "mrp_d": m_d,
                                        "created_at": get_ist_time().isoformat(),
                                    }
                                    supabase.table("stock").insert(payload).execute()

                                success_count += 1
                            except Exception as row_err:
                                error_count += 1

                        st.success(f"🎉 Successfully imported {success_count} stock items!")
                        if error_count > 0:
                            st.warning(f"⚠️ Skipped {error_count} invalid rows.")
                        st.session_state.pop("edited_df", None)
                        st.rerun()

            except Exception as file_err:
                st.error(f"Error reading file: {file_err}")
