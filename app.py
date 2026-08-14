import pandas as pd
import streamlit as st
from scraper import (
    extract_brand_and_category,
    extract_product_title_from_url,
    fetch_prices_via_api,
)

# Page configuration
st.set_page_config(
    page_title="Smart E-Commerce Price Tracker", page_icon="🛍️", layout="wide"
)

st.title("🛍️ Smart E-Commerce Price Comparison & Tracker")
st.write("Compare real-time product prices across Flipkart, Amazon, and Meesho.")

# Sidebar controls
st.sidebar.header("⚙️ API Settings")
rapidapi_key = st.sidebar.text_input(
    "RapidAPI Key",
    type="password",
    help="Enter your RapidAPI key to fetch live price data.",
)

# Search input form
with st.form(key="search_form"):
    url_input = st.text_input(
        "Enter Product URL (Flipkart, Amazon, or Meesho):",
        placeholder="https://www.amazon.in/dp/...",
    )
    search_btn = st.form_submit_button("🔍 Fetch Real Live Prices")

if search_btn:
    cleaned_url = url_input.strip()

    if not cleaned_url:
        st.warning("⚠️ Please enter a valid product URL.")
    elif not rapidapi_key.strip():
        st.error("🔑 Please enter your RapidAPI Key in the sidebar settings.")
    else:
        with st.spinner("Fetching live product data from platforms..."):
            product_title = extract_product_title_from_url(cleaned_url)
            brand, category, search_query = extract_brand_and_category(product_title)
            results, debug_info = fetch_prices_via_api(
                product_title, rapidapi_key, cleaned_url
            )

        st.subheader(f"📦 Product: **{product_title}**")

        # Debug Information Expander
        if debug_info:
            with st.expander("🔧 Status & Debug Info"):
                for platform, message in debug_info.items():
                    st.write(f"**{platform}:** {message}")

        # Render results only when verified numeric prices are fetched
        if results:
            sorted_results = sorted(results, key=lambda x: x["price"])
            cheapest = sorted_results[0]

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Lowest Price Platform", cheapest["platform"])
            col2.metric("Best Price", f"₹{int(cheapest['price']):,}")
            col3.metric("Stock Status", cheapest.get("stock", "In Stock"))
            col4.metric("Live Platforms Found", f"{len(results)}")

            st.markdown("---")

            # Platform Price Comparison Table
            st.subheader("📊 Live Platform Price Comparison Table")
            df = pd.DataFrame(results)

            df["price_display"] = df["price"].apply(lambda x: f"₹{int(x):,}")
            df["original_price_display"] = df["original_price"].apply(
                lambda x: f"₹{int(x):,}"
                if pd.notnull(x) and isinstance(x, (int, float)) and x > 0
                else "—"
            )

            df_display = df[
                [
                    "platform",
                    "price_display",
                    "original_price_display",
                    "stock",
                    "link_type",
                    "url",
                ]
            ].copy()
            df_display.columns = [
                "Platform",
                "Price (₹)",
                "Original Price (MRP)",
                "Stock Status",
                "Link Type",
                "Product URL",
            ]

            st.dataframe(
                df_display,
                use_container_width=True,
                column_config={
                    "Product URL": st.column_config.LinkColumn(
                        "Product Link", display_text="Visit Store"
                    )
                },
            )

            # Price Comparison Visualizer Chart
            st.markdown("---")
            st.subheader("📈 Price Comparison Visualizer")
            chart_df = (
                df[["platform", "price"]]
                .rename(columns={"platform": "Platform", "price": "Price (₹)"})
                .set_index("Platform")
            )
            st.bar_chart(chart_df)
        else:
            st.error(
                "❌ **No live price data could be retrieved.** Please verify your RapidAPI Key or input URL."
            )
