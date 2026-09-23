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
    for col in df.columns:
        if "created_at" in col or "date" in col or "time" in col or "updated_at" in col:
            try:
                df[col] = pd.to_datetime(df[col]).dt.tz_convert("Asia/Kolkata")
                df[col] = df[col].dt.strftime("%d/%b/%y %I:%M %p")
            except Exception:
                try:
                    df[col] = pd.to_datetime(df[col]).dt.strftime("%d/%b/%y %I:%M %p")
                except Exception:
                    pass
    return df


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
    "🎯 Product Insights (Fast & Dead Stock)",
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
elif menu == "📦 Live Stock":
    st.subheader("📦 Live Stock Inventory")
    try:
        response = supabase.table("stock").select("*").execute()
        df_stock = pd.DataFrame(response.data)

        if df_stock.empty:
            st.warning("No stock data found in Supabase database.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                gender_opts = df_stock["gender"].unique()
                gender_filter = st.multiselect(
                    "Gender Category",
                    options=gender_opts,
                    default=[],
                    placeholder="Select Gender...",
                )
            with col2:
                brand_opts = df_stock["product_name"].unique()
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

            # ADMIN ONLY EDITABLE TABLE
            if st.session_state.get("admin_logged_in", False):
                st.info("💡 **Admin Mode:** Double click on any cell (Qty, Price, Art No, etc.) to edit, then click **'💾 Save Changes to Database'** below.")
                
                edited_df = st.data_editor(
                    filtered_df,
                    key="stock_editor",
                    num_rows="dynamic",  # Rows add/delete panna mudiyum
                    disabled=["id", "created_at"],  # ID & Created time change panna mudiyadhu
                    use_container_width=True
                )

                if st.button("💾 Save Changes to Database", type="primary"):
                    try:
                        # Database update logic
                        for index, row in edited_df.iterrows():
                            row_id = row.get("id")
                            if pd.notnull(row_id):
                                update_payload = {
                                    "product_name": str(row["product_name"]),
                                    "gender": str(row["gender"]),
                                    "art_no": str(row["art_no"]),
                                    "size": str(row["size"]),
                                    "qty": int(row["qty"]),
                                    "price": float(row["price"])
                                }
                                supabase.table("stock").update(update_payload).eq("id", row_id).execute()
                        st.success("✅ Stock details updated successfully in Supabase!")
                        st.rerun()
                    except Exception as save_err:
                        st.error(f"Error saving changes: {save_err}")
            else:
                # VIEW ONLY FOR NORMAL USERS
                formatted_view = format_df_dates(filtered_df)
                st.dataframe(formatted_view, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching stock: {e}")
# ---------------------------------------------------------
# 2. SALES ANALYTICS (TODAY & HISTORY)
# ---------------------------------------------------------
elif menu == "📊 Sales Analytics":
    st.subheader("📊 Sales Analytics & Revenue")
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
                st.write(f"### 🗓️ Today's Sales ({today_date.strftime('%d/%b/%Y')})")
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
                total_qty = df_filtered["qty"].sum()
                total_rev = df_filtered["revenue"].sum()

                m1, m2 = st.columns(2)
                m1.metric("Total Pair Sales", f"{total_qty} Pairs")
                m2.metric("Total Revenue", f"₹{total_rev:,.2f}")

                df_filtered = format_df_dates(df_filtered)
                display_cols = [c for c in df_filtered.columns if c not in ["datetime_ist", "date_only"]]
                st.dataframe(
                    df_filtered[display_cols].sort_values(by="id", ascending=False),
                    use_container_width=True,
                )

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

# ---------------------------------------------------------
# 3. PRODUCT INSIGHTS (FAST & DEAD STOCK)
# ---------------------------------------------------------
elif menu == "🎯 Product Insights (Fast & Dead Stock)":
    st.subheader("🎯 Product Insights")

    tab1, tab2 = st.tabs(["🔥 Top / Fast Selling Products", "⚠️ Dead Stock (Zero Sales)"])

    # TAB 1: Fast Selling
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

    # TAB 2: Dead Stock
    with tab2:
        try:
            stock_res = supabase.table("stock").select("*").execute()
            sales_res = supabase.table("sales").select("*").execute()

            df_stock = pd.DataFrame(stock_res.data)
            df_sales = pd.DataFrame(sales_res.data)

            if df_stock.empty:
                st.info("Stock inventory is empty.")
            else:
                df_stock = format_df_dates(df_stock)

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
                st.dataframe(dead_stock, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading dead stock: {e}")

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
            # --- 1. Product ---
            products_list = list(df_stock["product_name"].unique())
            selected_product = st.selectbox(
                "Product",
                options=products_list,
                index=None,
                placeholder="Select Product...",
                key="sb_product",
            )

            # --- 2. Gender ---
            gender_list = []
            if selected_product:
                sub_1 = df_stock[df_stock["product_name"] == selected_product]
                gender_list = list(sub_1["gender"].unique())

            selected_gender = st.selectbox(
                "Gender",
                options=gender_list,
                index=None,
                placeholder="Select Gender...",
                key="sb_gender",
            )

            # --- 3. Art No ---
            art_list = []
            if selected_product and selected_gender:
                sub_2 = sub_1[sub_1["gender"] == selected_gender]
                art_list = list(sub_2["art_no"].unique())

            selected_art_no = st.selectbox(
                "Art No",
                options=art_list,
                index=None,
                placeholder="Select Art No...",
                key="sb_art_no",
            )

            # --- 4. Size ---
            size_list = []
            if selected_product and selected_gender and selected_art_no:
                sub_3 = sub_2[sub_2["art_no"] == selected_art_no]
                size_list = list(sub_3["size"].unique())

            selected_size = st.selectbox(
                "Size",
                options=size_list,
                index=None,
                placeholder="Select Size...",
                key="sb_size",
            )

            available_qty = 0
            item_price = 0.0
            selected_item = None

            if selected_product and selected_gender and selected_art_no and selected_size:
                matched_rows = sub_3[sub_3["size"] == selected_size]
                if not matched_rows.empty:
                    selected_item = matched_rows.iloc[0]
                    available_qty = selected_item.get("qty", 0)
                    item_price = selected_item.get("price", 0.0)

                    st.info(f"Available Quantity: **{available_qty}** | Price per pair: **₹{item_price}**")

            with st.form("exact_quick_sale_form"):
                col_qty, col_pay = st.columns(2)

                with col_qty:
                    sell_qty = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=max(1, int(available_qty)),
                        value=1,
                        key="num_qty",
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
                        "price": float(item_price),
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
                            f"FAYAS FOOTWEAR\nDate: {sale_date.strftime('%d/%b/%y')}\n"
                            f"Item: {selected_product} ({selected_gender})\n"
                            f"Art: {selected_art_no} | Size: {selected_size}\n"
                            f"Qty: {sell_qty} x ₹{item_price}\n"
                            f"Total: ₹{sell_qty * item_price}\n"
                            f"Payment: {payment_mode}"
                        )
                        qr_img = generate_qr_code(bill_details)

                        st.write("### 🧾 Digital Receipt")
                        st.text(bill_details)
                        st.image(qr_img, caption="Scan QR for Digital Bill Receipt")

    except Exception as e:
        st.error(f"Error during quick sale: {e}")

# ---------------------------------------------------------
# 5. STOCK UPDATE / NEW ENTRY (MANUAL)
# ---------------------------------------------------------
elif menu == "📝 Stock Update / New Entry" and st.session_state["admin_logged_in"]:
    st.subheader("📝 Manual Stock Entry / Add New Items")
    with st.form("manual_stock_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("Brand / Product Name (e.g., Walkaroo)")
            gender = st.selectbox("Gender", ["Gents", "Ladies", "Kids (B)", "Kids (G)"])
            art_no = st.text_input("Art No (e.g., W-102)")
        with col2:
            size = st.text_input("Size (e.g., 7 or 8)")
            qty = st.number_input("Quantity", min_value=1, value=12)
            price = st.number_input("Price (MRP)", min_value=0.0, value=350.0)

        submit_stock = st.form_submit_button("💾 Save / Update Stock")

        if submit_stock:
            if not product_name or not art_no or not size:
                st.error("Please fill all fields!")
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
                            "price": float(price),
                        }).eq("id", existing_row["id"]).execute()
                        st.success(f"Stock Updated! Added {qty} pairs to existing item. Total: {updated_qty}")
                    else:
                        payload = {
                            "product_name": product_name.strip(),
                            "gender": gender,
                            "art_no": art_no.strip(),
                            "size": str(size).strip(),
                            "qty": int(qty),
                            "price": float(price),
                            "created_at": get_ist_time().isoformat(),
                        }

                        supabase.table("stock").insert(payload).execute()
                        st.success("New Stock Item Created Successfully!")
                except Exception as e:
                    st.error(f"Failed to add stock: {e}")
