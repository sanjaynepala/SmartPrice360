import re
import requests
import urllib.parse

# Product categories dictionary (sorted longest-first)
PRODUCT_CATEGORIES = [
    # Beauty / Personal care
    "face wash", "face cream", "face serum", "face mask", "sunscreen",
    "moisturizer", "moisturiser", "shampoo", "conditioner", "hair oil",
    "body lotion", "body wash", "lip balm", "lipstick", "foundation",
    "perfume", "deodorant", "talcum powder", "hand wash", "face wipes",

    # Fashion - topwear/bottomwear
    "denim jacket", "leather jacket", "bomber jacket", "jacket",
    "hoodie", "sweatshirt", "sweater", "cardigan",
    "formal shirt", "casual shirt", "shirt", "t shirt", "tshirt",
    "jeans", "trousers", "joggers", "shorts", "track pants",
    "kurta", "kurti", "saree", "salwar suit", "lehenga", "dupatta",
    "dress", "gown", "skirt", "co ord set",

    # Footwear
    "running shoes", "sports shoes", "sneakers", "loafers", "sandals",
    "slippers", "flip flops", "formal shoes", "boots", "heels", "shoes",

    # Accessories
    "backpack", "handbag", "sling bag", "wallet", "belt", "sunglasses",
    "watch", "smartwatch", "cap", "hat", "scarf", "tie", "socks",

    # Electronics
    "smart phone", "mobile phone", "smartphone", "iphone", "laptop",
    "tablet", "ipad", "television", "smart tv", "tv", "refrigerator",
    "fridge", "washing machine", "air conditioner", "microwave oven",
    "earbuds", "headphones", "headphone", "earphones", "bluetooth speaker",
    "speaker", "power bank", "camera", "monitor", "keyboard", "mouse",
    "router", "processor", "graphics card",

    # Home & kitchen
    "mixer grinder", "pressure cooker", "non stick pan", "water bottle",
    "air fryer", "induction cooktop", "vacuum cleaner",
]
PRODUCT_CATEGORIES.sort(key=len, reverse=True)

# Platforms that are actually implemented and callable (used to keep UI copy honest)
IMPLEMENTED_PLATFORMS = ["Flipkart", "Amazon", "Meesho"]


def parse_price(val):
    """Safely parses numbers into clean integer values without mock fallback values."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val) if val > 0 else None
    if isinstance(val, dict):
        val = val.get("value") or val.get("price") or val.get("amount") or val.get("specialPrice")
        if val is None:
            return None
    cleaned = re.sub(r'[^\d.]', '', str(val).replace(',', ''))
    try:
        parsed = int(float(cleaned))
        return parsed if parsed > 0 else None
    except (ValueError, TypeError):
        return None


def extract_price_and_mrp_from_dict(p):
    """Extracts real current price and real original price (MRP) from API JSON objects."""
    if not isinstance(p, dict):
        return None, None

    # 1. Extract Current Price
    # NOTE: "product_price" was added because the real-time-amazon-data RapidAPI
    # response returns the current price under this exact key (e.g. "$19.99").
    # Without it, Amazon results always failed to parse a price even on a 200 OK
    # response with a valid product match.
    price = None
    for key in [
        "price", "current_price", "selling_price", "final_price",
        "special_price", "offer_price", "product_price",
    ]:
        val = p.get(key)
        parsed = parse_price(val)
        if parsed:
            price = parsed
            break

    if not price:
        pricing = p.get("pricing")
        if isinstance(pricing, dict):
            for key in ["finalPrice", "specialPrice", "sellingPrice", "currentPrice"]:
                val = pricing.get(key)
                parsed = parse_price(val)
                if parsed:
                    price = parsed
                    break

    # 2. Extract Real Original Price (MRP)
    original_price = None
    for key in [
        "original_price", "mrp", "list_price", "full_price",
        "retail_price", "product_original_price",
    ]:
        val = p.get(key)
        parsed = parse_price(val)
        if parsed:
            original_price = parsed
            break

    if not original_price:
        pricing = p.get("pricing")
        if isinstance(pricing, dict):
            for key in ["mrp", "originalPrice", "listPrice"]:
                val = pricing.get(key)
                parsed = parse_price(val)
                if parsed:
                    original_price = parsed
                    break

    # If original price is less than or equal to current price, set to None
    if original_price and price and original_price <= price:
        original_price = None

    return price, original_price


def extract_product_title_from_url(url):
    """Extracts a clean, human-readable product title from the URL path slug."""
    try:
        clean_url = url.split("?")[0]
        parts = [p for p in clean_url.split("/") if p]

        for part in reversed(parts):
            if "-" in part or "_" in part:
                title = part.replace("-", " ").replace("_", " ").title()
                # Strips trailing platform-specific product/item ID tokens such as
                # "P123456789", "ITM98765", "PID4567". A single regex covers all
                # three cases (any alpha run containing a digit right after the
                # leading letter(s)), so the separate itm/pid patterns that used
                # to duplicate this logic have been removed.
                title = re.sub(r'\b[a-zA-Z]{1,4}(?=\w*\d)\w+\b', '', title)
                cleaned = re.sub(r'\s+', ' ', title).strip()
                if len(cleaned) > 5:
                    return cleaned
    except Exception:
        pass
    return "Unknown Product"


def detect_category(title_lower):
    """Finds category match using exact regex word boundaries."""
    for category in PRODUCT_CATEGORIES:
        pattern = r'\b' + re.escape(category) + r'\b'
        if re.search(pattern, title_lower):
            return category
    return None


def extract_brand_and_category(product_title):
    """Extracts brand and category from product title."""
    title = re.sub(r'[^\w\s]', '', product_title).strip()
    title_lower = title.lower()

    category = detect_category(title_lower)

    if category:
        idx = title_lower.find(category)
        before = title[:idx].strip()
        before_words = before.split()

        if before_words:
            if len(before_words) >= 2 and len(before_words[0]) <= 3:
                brand = " ".join(before_words[:2])
            else:
                brand = before_words[0]
        else:
            brand = ""

        search_query = f"{brand} {category}".strip() if brand else category
        return brand, category, search_query

    words = title.split()
    if not words:
        return "", "", product_title

    if len(words) >= 2 and len(words[0]) <= 3:
        brand = f"{words[0]} {words[1]}"
    else:
        brand = words[0]

    search_query = " ".join(words[:5])
    return brand, "", search_query


def get_search_keywords(product_title, max_words=5):
    _, _, search_query = extract_brand_and_category(product_title)
    words = search_query.split()
    return " ".join(words[:max_words]) if words else product_title


def _find_first_product_list(data):
    if not isinstance(data, dict):
        return []

    candidate_keys = ["products", "results", "hits", "items"]
    for key in candidate_keys:
        val = data.get(key)
        if isinstance(val, list) and val:
            return val

    nested = data.get("data")
    if isinstance(nested, dict):
        for key in candidate_keys:
            val = nested.get(key)
            if isinstance(val, list) and val:
                return val
        if isinstance(nested, list) and nested:
            return nested
    if isinstance(nested, list) and nested:
        return nested

    return []


def fetch_flipkart_data(product_title, api_key):
    """Fetches real Flipkart price data via RapidAPI."""
    if not api_key:
        return {"price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "No RapidAPI key provided for Flipkart live data."}

    url = "https://real-time-flipkart-data2.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-flipkart-data2.p.rapidapi.com"
    }
    keywords = get_search_keywords(product_title)
    try:
        response = requests.get(url, headers=headers, params={"q": keywords}, timeout=8)

        if response.status_code != 200:
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": f"Flipkart API returned HTTP {response.status_code}."
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "Flipkart API returned 200 OK but no matching product found."
            }

        p = products[0]
        price, original_price = extract_price_and_mrp_from_dict(p)
        product_url = p.get("url") or p.get("product_url") or p.get("link")

        if not price:
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": f"Flipkart product found but no valid price returned from API. "
                         f"Raw keys seen: {list(p.keys())[:15]}"
            }

        return {"price": price, "original_price": original_price, "url": product_url, "is_available": True, "debug": None}

    except Exception as e:
        return {"price": None, "original_price": None, "url": None, "is_available": False, "debug": f"Flipkart API error: {e}"}


def fetch_amazon_data(product_title, api_key):
    """Fetches real Amazon price data via RapidAPI."""
    if not api_key:
        return {"price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "No RapidAPI key provided for Amazon live data."}

    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }
    keywords = get_search_keywords(product_title)
    try:
        response = requests.get(url, headers=headers, params={"query": keywords, "country": "IN"}, timeout=8)

        if response.status_code != 200:
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": f"Amazon API returned HTTP {response.status_code}."
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "Amazon API returned 200 OK but no matching product found."
            }

        p = products[0]
        price, original_price = extract_price_and_mrp_from_dict(p)
        product_url = p.get("product_url") or p.get("url")

        if not price:
            # Surface the raw keys in debug so a future field-name mismatch
            # (like the missing "product_price" key that caused this bug)
            # is easy to spot without re-reading the source.
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": f"Amazon product found but no valid price returned from API. "
                         f"Raw keys seen: {list(p.keys())[:15]}"
            }

        return {"price": price, "original_price": original_price, "url": product_url, "is_available": True, "debug": None}

    except Exception as e:
        return {"price": None, "original_price": None, "url": None, "is_available": False, "debug": f"Amazon API error: {e}"}


def fetch_meesho_data(product_title, api_key, user_url=""):
    """Fetches real Meesho data ONLY if a valid Meesho URL or API returns live data."""
    if not api_key:
        return {"price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "No RapidAPI key provided for Meesho live data."}

    if "meesho.com" not in user_url:
        return {"price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "Meesho requires a direct meesho.com product URL (it cannot be searched by title)."}

    url = "https://meesho-price-history-tracker4.p.rapidapi.com/meesho.php"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "meesho-price-history-tracker4.p.rapidapi.com"
    }
    payload = {"url": user_url}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = parse_price(data.get("price") or data.get("current_price"))
            original_price = parse_price(data.get("original_price") or data.get("mrp"))
            if price:
                return {
                    "price": price,
                    "original_price": original_price,
                    "url": user_url,
                    "is_available": True,
                    "debug": None
                }
            return {
                "price": None, "original_price": None, "url": None, "is_available": False,
                "debug": "Meesho API returned 200 OK but no valid price field was found."
            }

        return {
            "price": None, "original_price": None, "url": None, "is_available": False,
            "debug": f"Meesho API returned HTTP {response.status_code}."
        }
    except Exception as e:
        return {"price": None, "original_price": None, "url": None, "is_available": False, "debug": f"Meesho API error: {e}"}


def fetch_prices_via_api(product_title, api_key="", user_url=""):
    """
    Fetches real price data across platforms.
    ONLY includes platforms where actual real price data was successfully fetched.
    No random prices, no mock estimates, no ratings.
    """
    brand, category, search_keywords = extract_brand_and_category(product_title)
    encoded_query = urllib.parse.quote(search_keywords)

    fk_data = fetch_flipkart_data(product_title, api_key)
    az_data = fetch_amazon_data(product_title, api_key)
    ms_data = fetch_meesho_data(product_title, api_key, user_url)

    available_platforms = []
    debug_info = {}

    # 1. Flipkart
    if fk_data.get("is_available") and fk_data.get("price") is not None:
        fk_url = fk_data.get("url") or (user_url if "flipkart.com" in user_url else f"https://www.flipkart.com/search?q={encoded_query}")
        available_platforms.append({
            "platform": "Flipkart",
            "price": fk_data["price"],
            "original_price": fk_data.get("original_price"),
            "stock": "In Stock",
            "url": fk_url,
            "link_type": "Direct Product" if fk_data.get("url") or "flipkart.com" in user_url else "Search Results",
            "is_available": True
        })
    elif fk_data.get("debug"):
        debug_info["Flipkart"] = fk_data["debug"]

    # 2. Amazon
    if az_data.get("is_available") and az_data.get("price") is not None:
        az_url = az_data.get("url") or (user_url if "amazon." in user_url else f"https://www.amazon.in/s?k={encoded_query}")
        available_platforms.append({
            "platform": "Amazon",
            "price": az_data["price"],
            "original_price": az_data.get("original_price"),
            "stock": "In Stock",
            "url": az_url,
            "link_type": "Direct Product" if az_data.get("url") or "amazon." in user_url else "Search Results",
            "is_available": True
        })
    elif az_data.get("debug"):
        debug_info["Amazon"] = az_data["debug"]

    # 3. Meesho
    if ms_data.get("is_available") and ms_data.get("price") is not None:
        available_platforms.append({
            "platform": "Meesho",
            "price": ms_data["price"],
            "original_price": ms_data.get("original_price"),
            "stock": "In Stock",
            "url": ms_data.get("url") or user_url,
            "link_type": "Direct Product",
            "is_available": True
        })
    elif ms_data.get("debug"):
        debug_info["Meesho"] = ms_data["debug"]

    return available_platforms, debug_info
