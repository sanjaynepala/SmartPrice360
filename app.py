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
st.write("Compare product prices across Flipkart, Amazon, Meesho, Ajio, and Myntra.")

# Sidebar Controls for API Keys
st.sidebar.header("⚙️ Settings")
rapidapi_key = st.sidebar.text_input(
    "RapidAPI Key (Optional)",
    type="password",
    help="Optional: Enter key to fetch live Flipkart & Amazon prices via RapidAPI"
)

# Main UI Input
url_input = st.text_input(
    "Enter Product URL (Flipkart, Amazon, Meesho, Ajio, or Myntra):",
    placeholder="https://www.flipkart.com/..."
)
search_btn = st.button("🔍 Compare Prices Across Platforms")

if search_btn or url_input:
    if url_input.strip():
        with st.spinner("Fetching product data and searching across 5 platforms..."):
            product_title = extract_product_title_from_url(url_input)
            brand, category, search_query = extract_brand_and_category(product_title)
            results, debug_info = fetch_prices_via_api(product_title, rapidapi_key, url_input)

        st.subheader(f"📦 Product: **{product_title}**")
        
        if brand or category:
            st.caption(
                f"🔎 Searching platforms using: **{search_query}** "
                f"(Brand: `{brand or '—'}`, Category: `{category or '—'}`)"
            )
        else:
            st.caption(f"🔎 Searching platforms using: **{search_query}**")

        # Show Debug Expander if any API issues occur
        if debug_info:
            with st.expander("🔧 Debug Info (API & Platform Status)"):
                for platform, message in debug_info.items():
                    st.write(f"**{platform}:** {message}")

        if results:
            sorted_results = sorted(results, key=lambda x: x["price"])
            cheapest = sorted_results[0]
            
            # Key Metrics Cards (4 Columns)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lowest Price Platform", cheapest["platform"])
            col2.metric("Best Price", f"₹{cheapest['price']:,}")
            col3.metric("Status", cheapest["stock"])
            col4.metric("Available Platforms", f"{len(results)} of 5")

            st.markdown("---")

            # Platform Price Comparison Table
            st.subheader("📊 Platform Price Comparison Table")
            df = pd.DataFrame(results)
            df_display = df[["platform", "price", "original_price", "rating", "stock", "link_type", "url"]].copy()
            df_display.columns = ["Platform", "Price (₹)", "Original Price (₹)", "Rating ★", "Stock Status", "Link Type", "Product URL"]
            
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
            st.warning(f"⚠️ No matching platforms found for **{product_title}**.")
    else:
        st.warning("Please enter a valid product URL.")
