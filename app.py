import streamlit as st
import pandas as pd
from scraper import (
    extract_product_title_from_url,
    extract_brand_and_category,
    fetch_prices_via_api,
)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Smart E-Commerce Price Tracker",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Smart E-Commerce Price Comparison & Tracker")
st.write("Compare real-time product prices across Flipkart, Amazon, Meesho, Ajio, and Myntra.")

# Sidebar Controls for API Keys
st.sidebar.header("⚙️ API Settings")
rapidapi_key = st.sidebar.text_input(
    "RapidAPI Key",
    type="password",
    help="Enter your RapidAPI key to fetch live price data from supported platforms."
)

# Main UI Input
url_input = st.text_input(
    "Enter Product URL (Flipkart, Amazon, Meesho, Ajio, or Myntra):",
    placeholder="https://www.amazon.in/dp/..."
)
search_btn = st.button("🔍 Fetch & Compare Real Prices")

if search_btn or url_input:
    if url_input.strip():
        with st.spinner("Fetching live product data from platforms..."):
            product_title = extract_product_title_from_url(url_input)
            brand, category, search_query = extract_brand_and_category(product_title)
            results, debug_info = fetch_prices_via_api(product_title, rapidapi_key, url_input)

        st.subheader(f"📦 Product: **{product_title}**")
        
        if brand or category:
            st.caption(
                f"🔎 Searching using query: **{search_query}** "
                f"(Brand: `{brand or '—'}`, Category: `{category or '—'}`)"
            )
        else:
            st.caption(f"🔎 Searching using query: **{search_query}**")

        # Show Debug Expander if any API issues occur
        if debug_info:
            with st.expander("🔧 Status & Debug Info"):
                for platform, message in debug_info.items():
                    st.write(f"**{platform}:** {message}")

        if results:
            sorted_results = sorted(results, key=lambda x: x["price"])
            cheapest = sorted_results[0]
            
            # Key Metrics Cards (4 Columns - Rating section removed)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lowest Price Platform", cheapest["platform"])
            col2.metric("Best Price", f"₹{cheapest['price']:,}")
            col3.metric("Stock Status", cheapest["stock"])
            col4.metric("Available Platforms", f"{len(results)} of 5")

            st.markdown("---")

            # Platform Price Comparison Table
            st.subheader("📊 Live Platform Price Comparison Table")
            df = pd.DataFrame(results)
            
            # Format display prices cleanly without fake values
            df["price_display"] = df["price"].apply(lambda x: f"₹{int(x):,}")
            df["original_price_display"] = df["original_price"].apply(
                lambda x: f"₹{int(x):,}" if pd.notnull(x) and x is not None else "—"
            )

            df_display = df[["platform", "price_display", "original_price_display", "stock", "link_type", "url"]].copy()
            df_display.columns = ["Platform", "Price (₹)", "Original Price (MRP)", "Stock Status", "Link Type", "Product URL"]
            
            st.dataframe(
                df_display,
                use_container_width=True,
                column_config={
                    "Product URL": st.column_config.LinkColumn("Product Link", display_text="Visit Store")
                }
            )

            # Price Bar Chart
            st.markdown("---")
            st.subheader("📈 Price Comparison Visualizer")
            chart_df = df[["platform", "price"]].rename(columns={"platform": "Platform", "price": "Price (₹)"}).set_index("Platform")
            st.bar_chart(chart_df)
        else:
            st.warning(f"⚠️ No live price data could be fetched for **{product_title}**. Please enter a valid RapidAPI Key or direct product link.")
    else:
        st.warning("Please enter a valid product URL.")
