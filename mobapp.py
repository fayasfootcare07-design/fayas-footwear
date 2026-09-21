# --- 2. DEAD STOCK FINDER PAGE ---
elif choice == "❄️ Dead Stock Finder":
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
            
            days_filter = st.slider("Select Inactive Period (Days without sale):", min_value=7, max_value=120, value=30, step=7)
            
            sold_art_numbers = set()
            if not sales_df.empty:
                # Convert created_at to UTC timestamp safely
                sales_df["created_at"] = pd.to_datetime(sales_df["created_at"], utc=True)
                
                # Cutoff date with UTC timezone
                cutoff_date = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_filter)
                
                # Filter sales in selected days
                recent_sales = sales_df[sales_df["created_at"] >= cutoff_date]
                sold_art_numbers = set(recent_sales["art_no"].str.lower().unique())
            
            # Find stock items with no sales in these days
            stock_df["art_no_clean"] = stock_df["art_no"].astype(str).str.lower()
            dead_stock_df = stock_df[~stock_df["art_no_clean"].isin(sold_art_numbers) & (stock_df["quantity"] > 0)].copy()
            
            if not dead_stock_df.empty:
                dead_stock_df["locked_amount"] = dead_stock_df["quantity"] * dead_stock_df["price"]
                total_locked_capital = dead_stock_df["locked_amount"].sum()
                total_dead_pairs = dead_stock_df["quantity"].sum()
                
                m1, m2 = st.columns(2)
                m1.metric("🔴 Dead Stock Pairs", f"{total_dead_pairs} Pairs")
                m2.metric("💰 Locked Capital Amount", f"₹ {total_locked_capital:,.2f}")
                
                st.warning(f"⚠️ {len(dead_stock_df)} stock entries have **ZERO sales** in the last {days_filter} days!")
                
                st.dataframe(
                    dead_stock_df[["product", "gender", "art_no", "size", "quantity", "price", "locked_amount"]],
                    use_container_width=True,
                    hide_index=True
                )
                
                st.info("💡 **Business Advice:** Put discount banners or 'Clearance Sale' offers on these Art Nos to recover locked capital quickly!")
            else:
                st.success(f"🎉 Great job! No dead stock found for the last {days_filter} days. All items are moving well!")
        else:
            st.info("No stock data available.")
    except Exception as e:
        st.error(f"Error analyzing dead stock: {e}")
