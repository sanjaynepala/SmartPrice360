from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import urllib.parse
import requests

PRODUCT_CATEGORIES = [
    "face wash",
    "face cream",
    "face serum",
    "face mask",
    "sunscreen",
    "moisturizer",
    "shampoo",
    "conditioner",
    "hair oil",
    "body lotion",
    "body wash",
    "lip balm",
    "lipstick",
    "foundation",
    "perfume",
    "deodorant",
    "denim jacket",
    "leather jacket",
    "jacket",
    "hoodie",
    "sweatshirt",
    "sweater",
    "shirt",
    "t shirt",
    "tshirt",
    "jeans",
    "trousers",
    "joggers",
    "shorts",
    "kurta",
    "kurti",
    "saree",
    "running shoes",
    "sports shoes",
    "sneakers",
    "loafers",
    "sandals",
    "slippers",
    "backpack",
    "handbag",
    "wallet",
    "smartwatch",
    "watch",
    "smart phone",
    "mobile phone",
    "smartphone",
    "iphone",
    "laptop",
    "tablet",
    "tv",
    "earbuds",
    "headphones",
]
PRODUCT_CATEGORIES.sort(key=len, reverse=True)


def parse_price(val):
    """అసలైన ప్రైస్ మాత్రమే రిటర్న్ చేస్తుంది. లేకపోతే None ఇస్తుంది."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val) if val > 0 else None
    if isinstance(val, dict):
        val = (
            val.get("value")
            or val.get("price")
            or val.get("amount")
            or val.get("specialPrice")
        )
        if val is None:
            return None

    cleaned = re.sub(r"[^\d.]", "", str(val).replace(",", ""))
    try:
        parsed = int(float(cleaned))
        return parsed if parsed > 0 else None
    except (ValueError, TypeError):
        return None


def extract_price_and_mrp_from_dict(p):
    """API JSON నుండి ప్రైస్ మరియు MRP ఎక్స్‌ట్రాక్ట్ చేస్తుంది."""
    if not isinstance(p, dict):
        return None, None

    price = None
    for key in [
        "price",
        "current_price",
        "selling_price",
        "final_price",
        "special_price",
        "offer_price",
    ]:
        val = p.get(key)
        parsed = parse_price(val)
        if parsed:
            price = parsed
            break

    if not price:
        pricing = p.get("pricing")
        if isinstance(pricing, dict):
            for key in [
                "finalPrice",
                "specialPrice",
                "sellingPrice",
                "currentPrice",
            ]:
                val = pricing.get(key)
                parsed = parse_price(val)
                if parsed:
                    price = parsed
                    break

    original_price = None
    for key in [
        "original_price",
        "mrp",
        "list_price",
        "full_price",
        "retail_price",
        "product_original_price",
    ]:
        val = p.get(key)
        parsed = parse_price(val)
        if parsed:
            original_price = parsed
            break

    if original_price and price and original_price <= price:
        original_price = None

    return price, original_price


def extract_product_title_from_url(url):
    try:
        clean_url = url.split("?")[0]
        parts = [p for p in clean_url.split("/") if p]
        for part in reversed(parts):
            if "-" in part or "_" in part:
                title = part.replace("-", " ").replace("_", " ").title()
                title = re.sub(
                    r"\b([pP][iI][dD]|[iI][tT][mM]|[pP]|[aA][sS][iI][nN])\w*\d\w*\b",
                    "",
                    title,
                )
                cleaned = re.sub(r"\s+", " ", title).strip()
                if len(cleaned) > 5:
                    return cleaned
    except Exception:
        pass
    return "Unknown Product"


def detect_category(title_lower):
    for category in PRODUCT_CATEGORIES:
        pattern = r"\b" + re.escape(category) + r"\b"
        if re.search(pattern, title_lower):
            return category
    return None


def extract_brand_and_category(product_title):
    title = re.sub(r"[^\w\s]", "", product_title).strip()
    title_lower = title.lower()
    category = detect_category(title_lower)

    if category:
        idx = title_lower.find(category)
        before = title[:idx].strip()
        before_words = before.split()
        brand = before_words[0] if before_words else ""
        search_query = f"{brand} {category}".strip() if brand else category
        return brand, category, search_query

    words = title.split()
    if not words:
        return "", "", product_title

    brand = words[0]
    search_query = " ".join(words[:5])
    return brand, "", search_query


def get_search_keywords(product_title, max_words=5):
    _, _, search_query = extract_brand_and_category(product_title)
    words = search_query.split()
    return " ".join(words[:max_words]) if words else product_title


def fetch_flipkart_data(product_title, api_key):
    if not api_key:
        return {
            "platform": "Flipkart",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": "RapidAPI Key ఎంటర్ చేయలేదు.",
        }

    url = "https://real-time-flipkart-data2.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-flipkart-data2.p.rapidapi.com",
    }
    keywords = get_search_keywords(product_title)
    try:
        response = requests.get(
            url, headers=headers, params={"q": keywords}, timeout=6
        )
        if response.status_code != 200:
            return {
                "platform": "Flipkart",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": f"HTTP {response.status_code}",
            }

        data = response.json()
        products = data.get("products") or data.get("results") or []
        if not products:
            return {
                "platform": "Flipkart",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": "ప్రొడక్ట్ దొరకలేదు.",
            }

        p = products[0]
        price, original_price = extract_price_and_mrp_from_dict(p)
        product_url = p.get("url") or p.get("product_url") or p.get("link")

        if not price:
            return {
                "platform": "Flipkart",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": "ప్రైస్ లభించలేదు.",
            }

        return {
            "platform": "Flipkart",
            "price": price,
            "original_price": original_price,
            "url": product_url,
            "is_available": True,
            "debug": None,
        }
    except Exception as e:
        return {
            "platform": "Flipkart",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": str(e),
        }


def fetch_amazon_data(product_title, api_key):
    if not api_key:
        return {
            "platform": "Amazon",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": "RapidAPI Key ఎంటర్ చేయలేదు.",
        }

    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com",
    }
    keywords = get_search_keywords(product_title)
    try:
        response = requests.get(
            url,
            headers=headers,
            params={"query": keywords, "country": "IN"},
            timeout=6,
        )
        if response.status_code != 200:
            return {
                "platform": "Amazon",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": f"HTTP {response.status_code}",
            }

        data = response.json()
        products = data.get("data", {}).get("products") or data.get("products") or []
        if not products:
            return {
                "platform": "Amazon",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": "ప్రొడక్ట్ దొరకలేదు.",
            }

        p = products[0]
        price, original_price = extract_price_and_mrp_from_dict(p)
        product_url = p.get("product_url") or p.get("url")

        if not price:
            return {
                "platform": "Amazon",
                "price": None,
                "original_price": None,
                "url": None,
                "is_available": False,
                "debug": "ప్రైస్ లభించలేదు.",
            }

        return {
            "platform": "Amazon",
            "price": price,
            "original_price": original_price,
            "url": product_url,
            "is_available": True,
            "debug": None,
        }
    except Exception as e:
        return {
            "platform": "Amazon",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": str(e),
        }


def fetch_meesho_data(product_title, api_key, user_url=""):
    if not api_key or "meesho.com" not in user_url:
        return {
            "platform": "Meesho",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": "Meesho URL అవసరం.",
        }

    url = "https://meesho-price-history-tracker4.p.rapidapi.com/meesho.php"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "meesho-price-history-tracker4.p.rapidapi.com",
    }
    try:
        response = requests.post(url, data={"url": user_url}, headers=headers, timeout=6)
        if response.status_code == 200:
            data = response.json()
            price = parse_price(data.get("price") or data.get("current_price"))
            original_price = parse_price(data.get("original_price") or data.get("mrp"))
            if price:
                return {
                    "platform": "Meesho",
                    "price": price,
                    "original_price": original_price,
                    "url": user_url,
                    "is_available": True,
                    "debug": None,
                }
    except Exception as e:
        return {
            "platform": "Meesho",
            "price": None,
            "original_price": None,
            "url": None,
            "is_available": False,
            "debug": str(e),
        }

    return {
        "platform": "Meesho",
        "price": None,
        "original_price": None,
        "url": None,
        "is_available": False,
        "debug": "ప్రైస్ ఫెచ్ కాలేదు.",
    }


def fetch_prices_via_api(product_title, api_key="", user_url=""):
    _, _, search_keywords = extract_brand_and_category(product_title)
    encoded_query = urllib.parse.quote(search_keywords)

    available_platforms = []
    debug_info = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_flipkart_data, product_title, api_key): "Flipkart",
            executor.submit(fetch_amazon_data, product_title, api_key): "Amazon",
            executor.submit(fetch_meesho_data, product_title, api_key, user_url): "Meesho",
        }

        for future in as_completed(futures):
            platform_name = futures[future]
            try:
                res = future.result()
                # Strict Checking: price కచ్చితంగా నంబర్ మరియు > 0 ఉండాలి
                if res.get("is_available") and isinstance(res.get("price"), (int, float)) and res["price"] > 0:
                    fallback_url = (
                        f"https://www.amazon.in/s?k={encoded_query}"
                        if platform_name == "Amazon"
                        else f"https://www.flipkart.com/search?q={encoded_query}"
                    )
                    final_url = res.get("url") or (
                        user_url if platform_name.lower() in user_url.lower() else fallback_url
                    )

                    available_platforms.append(
                        {
                            "platform": platform_name,
                            "price": res["price"],
                            "original_price": res.get("original_price"),
                            "stock": "In Stock",
                            "url": final_url,
                            "link_type": (
                                "Direct Product"
                                if res.get("url") or platform_name.lower() in user_url.lower()
                                else "Search Results"
                            ),
                            "is_available": True,
                        }
                    )
                else:
                    if res.get("debug"):
                        debug_info[platform_name] = res["debug"]
            except Exception as exc:
                debug_info[platform_name] = f"Error: {exc}"

    return available_platforms, debug_info
