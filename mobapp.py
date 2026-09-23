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
    st.error(
        f"Secret Configuration Error: Check your Streamlit Secrets! Details: {e}"
    )
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
        if (
            "created_at" in col
            or "date" in col
            or "time" in col
            or "updated_at" in col
        ):
            try:
                df[col] = pd.to_datetime(df[col]).dt.tz_convert("Asia/Kolkata")
                df[col] = df[col].dt.strftime("%d/%b/%y %I:%M %p")
            except Exception:
                try:
                    df[col] = pd.to_datetime(df[col]).dt.strftime(
                        "%d/%b/%y %I:%M %p"
                    )
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
if menu == "📦 Live Stock":
    st.subheader("📦 Live Stock Inventory")
    try:
        response = supabase.table("stock").select("*").execute()
        df_stock = pd.DataFrame(response.data)

        if df_stock.empty:
            st.warning("No stock data found in Supabase database.")
        else:
            df_stock = format_df_dates(df_stock)
            prod_col = next(
                (
                    c
                    for c in ["product_name", "product", "item_name"]
                    if c in df_stock.columns
                ),
                None,
            )
            gender_col = next(
                (c for c in ["gender", "category"] if c in df_stock.columns),
                None,
            )

            if not prod_col:
                st.dataframe(df_stock, use_container_width=True)
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    gender_opts = (
                        df_stock[gender_col].unique()
                        if gender_col and gender_col in df_stock.columns
                        else []
                    )
                    gender_filter = st.multiselect(
                        "Gender Category",
                        options=gender_opts,
                        default=[],
                        placeholder="Select Gender...",
                    )
                with col2:
                    brand_opts = df_stock[prod_col].unique()
                    brand_filter = st.multiselect(
                        "Brand / Product",
                        options=brand_opts,
                        default=[],
                        placeholder="Select Brand...",
                    )
                with col3:
                    search_art = st.text_input("Search Art No", "")

                filtered_df = df_stock.copy()
                if (
                    gender_col
                    and gender_col in df_stock.columns
                    and gender_filter
                ):
                    filtered_df = filtered_df[
                        filtered_df[gender_col].isin(gender_filter)
                    ]
                if brand_filter:
                    filtered_df = filtered_df[
                        filtered_df[prod_col].isin(brand_filter)
                    ]
                if search_art and "art_no" in df_stock.columns:
                    filtered_df = filtered_df[
                        filtered_df["art_no"]
                        .astype(str)
                        .str.contains(search_art, case=False, na=False)
                    ]

                st.dataframe(filtered_df, use_container_width=True)

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
            qty_col = next(
                (c for c in ["qty", "quantity"] if c in df_sales.columns), "qty"
            )

            df_sales["datetime_ist"] = pd.to_datetime(
                df_sales["created_at"]
            ).dt.tz_convert("Asia/Kolkata")
            df_sales["date_only"] = df_sales["datetime_ist"].dt.date

            today_date = get_ist_time().date()

            view_type = st.radio(
                "Select Sales View:",
                ["🔥 Today's Live Sales", "📜 History Sales (By Date)"],
                horizontal=True,
            )

            if view_type == "🔥 Today's Live Sales":
                st.write(
                    f"### 🗓️ Today's Sales ({today_date.strftime('%d/%b/%Y')})"
                )
                df_filtered = df_sales[
                    df_sales["date_only"] == today_date
                ].copy()
            else:
                st.write("### 📜 Sales History")
                selected_date = st.date_input(
                    "Select Date for History",
                    value=today_date - timedelta(days=1),
                )
                df_filtered = df_sales[
                    df_sales["date_only"] == selected_date
                ].copy()

            if df_filtered.empty:
                st.warning("No sales recorded for this date.")
            else:
                df_filtered["revenue"] = (
                    df_filtered[qty_col] * df_filtered["price"]
                )
                total_qty = df_filtered[qty_col].sum()
                total_rev = df_filtered["revenue"].sum()

                m1, m2 = st.columns(2)
                m1.metric("Total Pair Sales", f"{total_qty} Pairs")
                m2.metric("Total Revenue", f"₹{total_rev:,.2f}")

                df_filtered = format_df_dates(df_filtered)
                display_cols = [
                    c
                    for c in df_filtered.columns
                    if c not in ["datetime_ist", "date_only"]
                ]
                st.dataframe(
                    df_filtered[display_cols].sort_values(
                        by="id", ascending=False
                    ),
                    use_container_width=True,
                )

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

# ---------------------------------------------------------
# 3. PRODUCT INSIGHTS (FAST & DEAD STOCK)
# ---------------------------------------------------------
elif menu == "🎯 Product Insights (Fast & Dead Stock)":
    st.subheader("🎯 Product Insights")

    tab1, tab2 = st.tabs(
        ["🔥 Top / Fast Selling Products", "⚠️ Dead Stock (Zero Sales)"]
    )

    # TAB 1: Fast Selling
    with tab1:
        try:
            sales_res = supabase.table("sales").select("*").execute()
            df_sales = pd.DataFrame(sales_res.data)

            if df_sales.empty:
                st.info("No sales data available yet.")
            else:
                qty_col = next(
                    (c for c in ["qty", "quantity"] if c in df_sales.columns),
                    "qty",
                )
                group_cols = [
                    c
                    for c in [
                        "product_name",
                        "product",
                        "gender",
                        "art_no",
                        "size",
                    ]
                    if c in df_sales.columns
                ]

                if group_cols and qty_col in df_sales.columns:
                    fast_selling = (
                        df_sales.groupby(group_cols)[qty_col]
                        .sum()
                        .reset_index()
                    )
                    fast_selling = fast_selling.sort_values(
                        by=qty_col, ascending=False
                    )
                    st.dataframe(fast_selling, use_container_width=True)
                else:
                    st.dataframe(df_sales, use_container_width=True)
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
                
                stock_prod_col = next(
                    (c for c in ["product_name", "product"] if c in df_stock.columns),
                    "product",
                )
                sales_prod_col = next(
                    (c for c in ["product_name", "product"] if c in df_sales.columns),
                    stock_prod_col if not df_sales.empty else "product",
                )

                if (
                    not df_sales.empty
                    and "art_no" in df_stock.columns
                    and "art_no" in df_sales.columns
                ):
                    df_sales_temp = df_sales.rename(columns={sales_prod_col: stock_prod_col})
                    
                    merge_cols = [c for c in [stock_prod_col, "gender", "art_no", "size"] if c in df_stock.columns and c in df_sales_temp.columns]
                    
                    sold_items = df_sales_temp[merge_cols].drop_duplicates()
                    dead_stock = pd.merge(
                        df_stock,
                        sold_items,
                        on=merge_cols,
                        how="left",
                        indicator=True,
                    )
                    dead_stock = dead_stock[
                        dead_stock["_merge"] == "left_only"
                    ].drop(columns=["_merge"])
                else:
                    dead_stock = df_stock

                st.warning(
                    f"Found {len(dead_stock)} stock items with zero sales record:"
                )
                st.dataframe(dead_stock, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading dead stock: {e}")

# ---------------------------------------------------------
# 4. QUICK SALE ENTRY (WITH ENTER KEY AUTO FOCUS JUMP)
# ---------------------------------------------------------
elif menu == "➕ Quick Sale Entry" and st.session_state["admin_logged_in"]:
    st.subheader("Quick Sale Entry")

    # JavaScript script to jump to next input on Enter key press
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
            st.error("No stock available in database!")
        else:
            prod_col = next(
                (c for c in ["product_name", "product"] if c in df_stock.columns),
                "product",
            )
            qty_col = next(
                (c for c in ["qty", "quantity"] if c in df_stock.columns), "qty"
            )

            # --- 1. Product ---
            products_list = list(df_stock[prod_col].unique())
            selected_product = st.selectbox(
                "Product",
                options=products_list,
                index=None,
                placeholder="Select Product...",
                key="sb_product"
            )

            # --- 2. Gender ---
            gender_list = []
            if selected_product:
                sub_1 = df_stock[df_stock[prod_col] == selected_product]
                if "gender" in sub_1.columns:
                    gender_list = list(sub_1["gender"].unique())

            selected_gender = st.selectbox(
                "Gender",
                options=gender_list,
                index=None,
                placeholder="Select Gender...",
                key="sb_gender"
            )

            # --- 3. Art No ---
            art_list = []
            if selected_product and selected_gender:
                sub_2 = sub_1[sub_1["gender"] == selected_gender] if "gender" in sub_1.columns else sub_1
                if "art_no" in sub_2.columns:
                    art_list = list(sub_2["art_no"].unique())

            selected_art_no = st.selectbox(
                "Art No",
                options=art_list,
                index=None,
                placeholder="Select Art No...",
                key="sb_art_no"
            )

            # --- 4. Size ---
            size_list = []
            if selected_product and selected_gender and selected_art_no:
                sub_3 = sub_2[sub_2["art_no"] == selected_art_no] if "art_no" in sub_2.columns else sub_2
                if "size" in sub_3.columns:
                    size_list = list(sub_3["size"].unique())

            selected_size = st.selectbox(
                "Size",
                options=size_list,
                index=None,
                placeholder="Select Size...",
                key="sb_size"
            )

            # Fetch matched item details
            available_qty = 0
            item_price = 0.0
            selected_item = None

            if selected_product and selected_gender and selected_art_no and selected_size:
                matched_rows = sub_3[sub_3["size"] == selected_size] if "size" in sub_3.columns else sub_3
                if not matched_rows.empty:
                    selected_item = matched_rows.iloc[0]
                    available_qty = selected_item.get(qty_col, 0)
                    item_price = selected_item.get("price", 0.0)

                    st.info(
                        f"Available Quantity: **{available_qty}** | Price per pair: **₹{item_price}**"
                    )

            # --- Form: Quantity, Payment, Sale Date & Buttons ---
            with st.form("exact_quick_sale_form"):
                col_qty, col_pay = st.columns(2)

                with col_qty:
                    sell_qty = st.number_input(
                        "Quantity",
                        min_value=1,
                        max_value=max(1, int(available_qty)),
                        value=1,
                        key="num_qty"
                    )

                with col_pay:
                    payment_mode = st.radio(
                        "Payment",
                        options=["Cash", "UPI"],
                        horizontal=True
                    )

                # --- Sale Date ---
                sale_date = st.date_input(
                    "Sale Date",
                    value=get_ist_time().date()
                )

                # --- Bottom Action Buttons ---
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submit_sale = st.form_submit_button("Sale")
                with col_btn2:
                    generate_qr_btn = st.form_submit_button("Generate QR")

            # --- Action Handler ---
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

                    sale_res = (
                        supabase.table("sales").select("*").limit(1).execute()
                    )
                    s_cols = list(sale_res.data[0].keys()) if (sale_res.data and len(sale_res.data) > 0) else []
                    s_qty_key = "quantity" if "quantity" in s_cols else "qty"
                    s_prod_key = "product" if "product" in s_cols else "product_name"

                    sale_data = {
                        "gender": selected_gender,
                        "art_no": selected_art_no,
                        "size": str(selected_size),
                        "price": float(item_price),
                        "created_at": custom_datetime,
                    }
                    sale_data[s_qty_key] = int(sell_qty)
                    sale_data[s_prod_key] = selected_product

                    if "payment_mode" in s_cols or "payment" in s_cols:
                        pay_key = "payment_mode" if "payment_mode" in s_cols else "payment"
                        sale_data[pay_key] = payment_mode
                    else:
                        sale_data["payment_mode"] = payment_mode

                    if submit_sale:
                        supabase.table("sales").insert(sale_data).execute()

                        new_qty = max(0, int(available_qty) - int(sell_qty))
                        supabase.table("stock").update({qty_col: new_qty}).eq(
                            "id", selected_item["id"]
                        ).execute()

                        st.success(f"Sale Recorded ({payment_mode}) & Stock Deducted Successfully!")

                    if generate_qr_btn or submit_sale:
                        bill_details = (
                            f"FAYAS FOOTWEAR\nDate:"
                            f" {sale_date.strftime('%d/%b/%y')}\nItem: {selected_product}"
                            f" ({selected_gender})\nArt: {selected_art_no} | Size: {selected_size}\nQty: {sell_qty}"
                            f" x ₹{item_price}\nTotal: ₹{sell_qty * item_price}\nPayment: {payment_mode}"
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
elif (
    menu == "📝 Stock Update / New Entry" and st.session_state["admin_logged_in"]
):
    st.subheader("📝 Manual Stock Entry / Add New Items")
    with st.form("manual_stock_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input(
                "Brand / Product Name (e.g., Walkaroo)"
            )
            gender = st.selectbox(
                "Gender", ["Gents", "Ladies", "Kids (B)", "Kids (G)"]
            )
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
                    all_stock = (
                        supabase.table("stock").select("*").execute()
                    )
                    df_all = (
                        pd.DataFrame(all_stock.data)
                        if all_stock.data
                        else pd.DataFrame()
                    )

                    prod_key = (
                        "product"
                        if "product" in df_all.columns
                        else "product_name"
                    )
                    qty_key = (
                        "quantity" if "quantity" in df_all.columns else "qty"
                    )

                    # Check if already exists
                    existing = pd.DataFrame()
                    if not df_all.empty:
                        existing = df_all[
                            (
                                df_all[prod_key].astype(str).str.lower()
                                == product_name.strip().lower()
                            )
                            & (
                                df_all["gender"].astype(str).str.lower()
                                == gender.strip().lower()
                            )
                            & (
                                df_all["art_no"].astype(str).str.lower()
                                == art_no.strip().lower()
                            )
                            & (
                                df_all["size"].astype(str)
                                == str(size).strip()
                            )
                        ]

                    if not existing.empty:
                        # UPDATE existing stock Qty
                        existing_row = existing.iloc[0]
                        updated_qty = int(existing_row[qty_key]) + int(qty)
                        supabase.table("stock").update({
                            qty_key: updated_qty,
                            "price": float(price),
                        }).eq("id", existing_row["id"]).execute()
                        st.success(
                            f"Stock Updated! Added {qty} pairs to existing"
                            f" item. Total: {updated_qty}"
                        )
                    else:
                        # INSERT new item
                        payload = {
                            "gender": gender,
                            "art_no": art_no.strip(),
                            "size": str(size).strip(),
                            "price": float(price),
                            "created_at": get_ist_time().isoformat(),
                        }
                        payload[prod_key] = product_name.strip()
                        payload[qty_key] = int(qty)

                        supabase.table("stock").insert(payload).execute()
                        st.success("New Stock Item Created Successfully!")
                except Exception as e:
                    st.error(f"Failed to add stock: {e}")
