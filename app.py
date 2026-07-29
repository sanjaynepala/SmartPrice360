import streamlit as st
import pandas as pd
from database import init_db, save_price
from scraper import extract_product_title_from_url, fetch_prices_via_api

st.set_page_config(
    page_title="Smart E-Commerce Price Tracker",
    page_icon="🛍️",
    layout="wide"
)

init_db()

st.title("🛍️ Smart E-Commerce Price Comparison & Tracker")
st.write("Compare product prices across Flipkart, Amazon, Meesho, Ajio, and Myntra.")

# Sidebar Configuration for Private Key
st.sidebar.header("⚙️ Security & API Configuration")

# Streamlit Secrets nunchi check chesthundhi leda Manual Sidebar Input teesukuntundhi
rapidapi_key = ""
if "RAPIDAPI_KEY" in st.secrets:
    rapidapi_key = st.secrets["RAPIDAPI_KEY"]
else:
    rapidapi_key = st.sidebar.text_input(
        "Enter RapidAPI Key:", 
        type="password", 
        help="Keep your API key private. Enter it here for live API fetching."
    )

st.sidebar.markdown("---")
st.sidebar.info("🔒 Code contains no hardcoded keys. Safe for GitHub & Cloud deployment.")

# Product Input Section
url_input = st.text_input(
    "Enter Product URL:",
    placeholder="https://www.flipkart.com/... or https://www.meesho.com/..."
)

search_btn = st.button("🔍 Search & Compare Prices", type="primary")

if search_btn or url_input:
    if url_input.strip():
        with st.spinner("Fetching product data and prices..."):
            product_title = extract_product_title_from_url(url_input)
            st.subheader(f"📦 Product: **{product_title}**")
            
            results = fetch_prices_via_api(product_title, rapidapi_key, url_input)
            
            if results:
                sorted_results = sorted(results, key=lambda x: x["price"])
                cheapest = sorted_results[0]
                
                for r in results:
                    save_price(product_title, r["platform"], r["price"])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Lowest Price Platform", cheapest["platform"])
                col2.metric("Best Price", f"₹{cheapest['price']}")
                col3.metric("Status", cheapest["stock"])
                
                st.markdown("---")
                
                st.subheader("📊 Platform Price Comparison Table")
                df = pd.DataFrame(results)
                df_display = df[["platform", "price", "original_price", "rating", "stock", "url"]].copy()
                df_display.columns = ["Platform", "Current Price (₹)", "Original Price (₹)", "Rating", "Stock", "Product Link"]
                
                st.dataframe(
                    df_display, 
                    column_config={"Product Link": st.column_config.LinkColumn("Product Link")},
                    use_container_width=True
                )
                
                st.subheader("📈 Price Comparison Chart")
                chart_df = pd.DataFrame({
                    "Platform": [r["platform"] for r in results],
                    "Price (₹)": [r["price"] for r in results]
                }).set_index("Platform")
                
                st.bar_chart(chart_df)
    else:
        st.warning("Please enter a valid product URL.")
