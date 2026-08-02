import streamlit as st
import pandas as pd
from database import init_db, save_price, get_price_history
from scraper import extract_product_title_from_url, fetch_prices_via_api

st.set_page_config(
    page_title="Smart E-Commerce Price Tracker",
    page_icon="🛍️",
    layout="wide"
)

# Initialize database tables
init_db()

st.title("🛍️ Smart E-Commerce Price Comparison & Tracker")
st.write("Compare product prices across Flipkart, Amazon, Meesho, Ajio, and Myntra.")

# Sidebar Configuration for RapidAPI Key
st.sidebar.header("⚙️ Configuration")

rapidapi_key = ""
if "RAPIDAPI_KEY" in st.secrets:
    rapidapi_key = st.secrets["RAPIDAPI_KEY"]
else:
    rapidapi_key = st.sidebar.text_input(
        "Enter RapidAPI Key:", 
        type="password", 
        help="Enter key here or set up st.secrets for automatic loading."
    )

st.sidebar.markdown("---")
st.sidebar.info("🔒 Code contains no hardcoded keys. Safe for GitHub & Cloud deployment.")

# Input Section
url_input = st.text_input(
    "Enter Product URL:",
    placeholder="https://www.flipkart.com/... or https://www.meesho.com/... or https://www.amazon.in/..."
)

search_btn = st.button("🔍 Search & Compare Prices", type="primary")

if search_btn or url_input:
    if url_input.strip():
        with st.spinner("Fetching product data and verifying brand availability across platforms..."):
            product_title = extract_product_title_from_url(url_input)
            st.subheader(f"📦 Product: **{product_title}**")
            
            results = fetch_prices_via_api(product_title, rapidapi_key, url_input)
            
            if results:
                sorted_results = sorted(results, key=lambda x: x["price"])
                cheapest = sorted_results[0]
                
                # Save available prices to database
                for r in results:
                    save_price(product_title, r["platform"], r["price"])
                
                # Key Metrics Cards
                col1, col2, col3 = st.columns(3)
                col1.metric("Lowest Price Platform", cheapest["platform"])
                col2.metric("Best Price", f"₹{cheapest['price']}")
                col3.metric("Available Platforms", f"{len(results)} of 5")
                
                st.markdown("---")
                
                # Comparison Dataframe Table (Only verified available platforms are shown)
                st.subheader("📊 Platform Price Comparison Table")
                df = pd.DataFrame(results)
                df_display = df[["platform", "price", "original_price", "rating", "stock", "link_type", "url"]].copy()
                df_display.columns = ["Platform", "Current Price (₹)", "Original Price (₹)", "Rating", "Stock", "Link Type", "Product Link"]
                
                st.dataframe(
                    df_display, 
                    column_config={
                        "Product Link": st.column_config.LinkColumn("Product Link"),
                        "Link Type": st.column_config.TextColumn("Link Type")
                    },
                    use_container_width=True
                )
                
                # Price Comparison Bar Chart
                st.subheader("📈 Price Comparison Chart")
                chart_df = pd.DataFrame({
                    "Platform": [r["platform"] for r in results],
                    "Price (₹)": [r["price"] for r in results]
                }).set_index("Platform")
                
                st.bar_chart(chart_df)
                
                # Saved Price History Table
                history = get_price_history(product_title)
                if history:
                    st.markdown("---")
                    st.subheader("📜 Recorded Price History (Database)")
                    hist_df = pd.DataFrame(history, columns=["Platform", "Price (₹)", "Timestamp"])
                    st.dataframe(hist_df, use_container_width=True)
            else:
                st.warning(f"⚠️ No matching platforms found for **{product_title}**.")
    else:
        st.warning("Please enter a valid product URL.")
