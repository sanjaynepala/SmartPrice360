# 🛍️ SmartPrice360 — Smart E-Commerce Price Comparison & Tracker

Compare product prices across **Flipkart, Amazon, Meesho, Ajio, and Myntra** by simply pasting a product link from any one of them.

🔗 **Live App:** https://smartprice-360.streamlit.app/

---

## ✨ Features

- 🔗 **Paste any product URL** (Flipkart, Amazon, Meesho, Ajio, or Myntra) and instantly compare its price across the other platforms.
- 🧠 **Smart brand + category detection** — automatically extracts the product's brand and category from the URL (e.g. `Ethiglo` + `Face Wash`, `Highlander` + `Denim Jacket`) instead of using the full noisy title, so cross-platform search stays accurate.
- ✅ **Verified availability filtering** — only platforms where the product/brand is genuinely available are shown. If a product isn't available on a platform, it's excluded instead of showing incorrect data.
- 📊 **Price comparison table** with current price, original price, rating, stock status, and direct product links.
- 📈 **Visual bar chart** comparing prices across all available platforms.
- 🏆 **Best price highlight** — instantly see the cheapest platform and price.
- 🔧 **Debug panel** — transparently shows why a platform was excluded (API errors, missing data, etc.) instead of failing silently.
- 🔒 **No hardcoded API keys** — safe to deploy publicly on GitHub/Streamlit Cloud.

---

## 🧰 Tech Stack

- **[Streamlit](https://streamlit.io/)** — web app framework
- **[Pandas](https://pandas.pydata.org/)** — data handling and display
- **[Requests](https://docs.python-requests.org/)** — API calls and live availability checks
- **[RapidAPI](https://rapidapi.com/)** — Flipkart & Amazon live price data

---

## 📁 Project Structure

```
├── app.py         # Streamlit UI — input, results table, chart, debug panel
├── scraper.py      # Core logic — title/brand/category extraction, API calls, availability checks
└── README.md
```

---

## ⚙️ How It Works

1. **Paste a product URL** from any supported platform.
2. The app extracts a clean **product title** from the URL slug.
3. It then detects the **brand** and **product category** (e.g. "Ethiglo" + "Face Wash") to build a short, accurate search query — instead of searching with the full descriptive title.
4. Using this query, it:
   - Fetches **live prices** from Flipkart & Amazon via RapidAPI (if a key is provided).
   - Estimates/fetches Meesho pricing.
   - Runs a **live availability check** on Meesho, Ajio, and Myntra to confirm the brand genuinely appears in their search results.
5. Only platforms confirmed to have the product are shown — with price, rating, stock, and a direct link.

---

## 🔑 Setup — RapidAPI Key

Live Flipkart & Amazon prices require a [RapidAPI](https://rapidapi.com/) key with an active subscription to:

- `real-time-flipkart-data2`
- `real-time-amazon-data`

**Option 1 — Streamlit Secrets (recommended for deployment)**

Add to `.streamlit/secrets.toml`:

```toml
RAPIDAPI_KEY = "your_rapidapi_key_here"
```

**Option 2 — Enter it directly in the app sidebar** (useful for local testing).

> ⚠️ Without a key, Flipkart and Amazon results won't appear (Meesho/Ajio/Myntra will still show based on availability checks).

---

## 🚀 Running Locally

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd <your-repo-folder>

# 2. Install dependencies
pip install streamlit pandas requests

# 3. Run the app
streamlit run app.py
```

---

## 🐛 Troubleshooting

If a platform (e.g. Flipkart) doesn't show up in results, expand the **🔧 Debug Info** panel in the app — it shows the exact reason (API error code, missing subscription, timeout, etc.) instead of failing silently.

---

## 📌 Notes

- This project relies on third-party APIs and live page scraping for availability checks — results depend on the uptime/format of those sources.
- Built for the Indian e-commerce market (₹ pricing, `.in` domains).
