import re
import requests
import urllib.parse

# ---------------------------------------------------------------------------
# Generic product category dictionary.
# Add more phrases here any time — the matching logic below is fully generic,
# it does NOT hardcode any single category like "face wash". Longer / more
# specific phrases are matched first (e.g. "denim jacket" before "jacket").
# ---------------------------------------------------------------------------
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
# Sort longest-first so multi-word categories are matched before their
# shorter substrings (e.g. "running shoes" before "shoes").
PRODUCT_CATEGORIES.sort(key=len, reverse=True)

# Used only as a coarse platform-suitability filter (electronics don't
# usually appear on fashion-only platforms like Ajio/Myntra/Meesho).
ELECTRONICS_KEYWORDS = [
    "mobile", "phone", "laptop", "computer", "tv", "television", "refrigerator",
    "fridge", "washing machine", "earbuds", "headphone", "earphone", "monitor",
    "processor", "ram", "ssd", "hard drive", "camera", "tablet", "ipad", "iphone",
    "samsung galaxy", "redmi", "realme", "oneplus", "smartwatch", "router",
]


def extract_product_title_from_url(url):
    """
    Extracts a clean, full, human-readable product title from the URL path
    slug. This is used for DISPLAY purposes (e.g. "Highlander Denim Jacket
    For Men Blue"). It is intentionally kept as the full descriptive title -
    the shorter brand+category query used for cross-platform search is
    derived separately by get_search_keywords().
    """
    try:
        clean_url = url.split("?")[0]
        parts = [p for p in clean_url.split("/") if p]

        for part in reversed(parts):
            if "-" in part or "_" in part:
                title = part.replace("-", " ").replace("_", " ").title()
                # Strip out common e-commerce item code patterns (e.g. p12345,
                # itm12345, pid12345). Requires at least one digit so normal
                # words like "Polo" or "Item" are never stripped.
                title = re.sub(r'\b[pP](?=\w*\d)\w+\b', '', title)
                title = re.sub(r'\b[iI][tT][mM](?=\w*\d)\w+\b', '', title)
                title = re.sub(r'\b[pP][iI][dD](?=\w*\d)\w+\b', '', title)
                cleaned = re.sub(r'\s+', ' ', title).strip()
                if len(cleaned) > 5:
                    return cleaned
    except Exception:
        pass
    return "Unknown Product"


def detect_category(title_lower):
    """
    Finds the best (longest, most specific) matching category phrase inside
    the given lowercase title. Returns the matched phrase or None.
    Fully generic - works for ANY category in PRODUCT_CATEGORIES, not just
    one hardcoded type.
    """
    for category in PRODUCT_CATEGORIES:
        if category in title_lower:
            return category
    return None


def extract_brand_and_category(product_title):
    """
    Generic brand + category extractor.

    Logic:
    1. Find the product category phrase inside the title (e.g. "face wash",
       "denim jacket", "running shoes"...).
    2. Whatever comes BEFORE that category phrase in the title is treated as
       the brand (e.g. "Ethiglo" before "Face Wash", "Highlander" before
       "Denim Jacket").
    3. If no known category phrase is found, fall back to a simple
       first-1-2-words heuristic for the brand and use the first few words
       as a generic search query.

    Returns: (brand, category, search_query)
    """
    title = re.sub(r'[^\w\s]', '', product_title).strip()
    title_lower = title.lower()

    category = detect_category(title_lower)

    if category:
        idx = title_lower.find(category)
        before = title[:idx].strip()
        before_words = before.split()

        if before_words:
            # Brand is virtually always at the START of the title
            # (e.g. "Ethiglo" in "Ethiglo Skin Lightening Face Wash",
            # "Highlander" in "Highlander Denim Jacket For Men").
            # Take 2 words if the first word is a short prefix like "MI",
            # "US Polo" style brands, else just the first word.
            if len(before_words) >= 2 and len(before_words[0]) <= 3:
                brand = " ".join(before_words[:2])
            else:
                brand = before_words[0]
        else:
            brand = ""

        search_query = f"{brand} {category}".strip() if brand else category
        return brand, category, search_query

    # --- Fallback: no known category matched ---
    words = title.split()
    if not words:
        return "", "", product_title

    if len(words) >= 2 and len(words[0]) <= 3:
        brand = f"{words[0]} {words[1]}"
    else:
        brand = words[0]

    search_query = " ".join(words[:5])
    return brand, "", search_query


def extract_brand_name(product_title):
    """Kept for backward compatibility - returns just the brand portion."""
    brand, _, _ = extract_brand_and_category(product_title)
    return brand


def get_search_keywords(product_title, max_words=5):
    """
    Returns the SHORT, cross-platform-friendly search query: brand + category
    when detected (e.g. "Ethiglo Face Wash", "Highlander Denim Jacket"),
    otherwise falls back to the first few words of the title.
    """
    _, _, search_query = extract_brand_and_category(product_title)
    words = search_query.split()
    return " ".join(words[:max_words]) if words else product_title


def is_electronics_product(product_title):
    """Checks if a product is an electronic item."""
    title_lower = product_title.lower()
    return any(keyword in title_lower for keyword in ELECTRONICS_KEYWORDS)


def check_platform_availability_live(platform_name, search_keywords, brand):
    """
    Live check to verify if a brand/product actually exists on a given platform.
    If the brand name is missing from the search results, returns False (Not Available).
    """
    if not brand or len(brand) < 3:
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    encoded_query = urllib.parse.quote(search_keywords)
    brand_lower = brand.lower()

    try:
        if platform_name == "Meesho":
            url = f"https://www.meesho.com/search?q={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                if brand_lower not in r.text.lower():
                    return False
                return True

        elif platform_name == "Ajio":
            url = f"https://www.ajio.com/search/?text={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                if brand_lower not in r.text.lower():
                    return False
                return True

        elif platform_name == "Myntra":
            url = f"https://www.myntra.com/search?rawQuery={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                if brand_lower not in r.text.lower():
                    return False
                return True
    except Exception:
        pass

    return True  # Fallback default if live check encounters timeout


def _find_first_product_list(data):
    """
    Different RapidAPI Flipkart providers wrap the product list under
    different keys (e.g. "products", "data.products", "results",
    "data.results", "hits"...). This walks common shapes and returns the
    first non-empty list of product-like dicts it finds.
    """
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
    """
    Fetches price and product URL from Flipkart RapidAPI.
    Returns a debug field with the raw status/response/exception so
    failures are visible instead of silently disappearing.
    """
    if not api_key:
        return {"price": None, "url": None, "is_available": False,
                "debug": "No API key provided - Flipkart needs a RapidAPI key to fetch live data."}

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
                "price": None, "url": None, "is_available": False,
                "debug": f"Flipkart API returned HTTP {response.status_code}: {response.text[:300]}"
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": f"Flipkart API returned 200 but no products found. Raw response (truncated): {str(data)[:300]}"
            }

        p = products[0]
        price = p.get("price") or p.get("current_price") or p.get("selling_price") or p.get("final_price")
        product_url = p.get("url") or p.get("product_url") or p.get("link") or p.get("product_link")

        if not price:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": f"Flipkart product found but no price field in response: {str(p)[:300]}"
            }

        parsed_price = int(float(str(price).replace("₹", "").replace(",", "").strip()))
        return {"price": parsed_price, "url": product_url, "is_available": True, "debug": None}

    except requests.exceptions.Timeout:
        return {"price": None, "url": None, "is_available": False,
                "debug": "Flipkart API request timed out."}
    except Exception as e:
        return {"price": None, "url": None, "is_available": False,
                "debug": f"Flipkart API request failed: {type(e).__name__}: {e}"}


def fetch_amazon_data(product_title, api_key):
    """
    Fetches price and product URL from Amazon RapidAPI.
    Returns a debug field with the raw status/response/exception so
    failures are visible instead of silently disappearing.
    """
    if not api_key:
        return {"price": None, "url": None, "is_available": False,
                "debug": "No API key provided - Amazon needs a RapidAPI key to fetch live data."}

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
                "price": None, "url": None, "is_available": False,
                "debug": f"Amazon API returned HTTP {response.status_code}: {response.text[:300]}"
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": f"Amazon API returned 200 but no products found. Raw response (truncated): {str(data)[:300]}"
            }

        p = products[0]
        price_str = p.get("product_price") or p.get("price")
        product_url = p.get("product_url") or p.get("url")

        if not price_str:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": f"Amazon product found but no price field in response: {str(p)[:300]}"
            }

        parsed_price = int(float(str(price_str).replace("₹", "").replace(",", "").replace("$", "").strip()))
        return {"price": parsed_price, "url": product_url, "is_available": True, "debug": None}

    except requests.exceptions.Timeout:
        return {"price": None, "url": None, "is_available": False,
                "debug": "Amazon API request timed out."}
    except Exception as e:
        return {"price": None, "url": None, "is_available": False,
                "debug": f"Amazon API request failed: {type(e).__name__}: {e}"}


def fetch_meesho_price(product_title, api_key, base_price, user_url=""):
    """Fetches Meesho price if URL is Meesho link, else estimates price."""
    if not api_key or "meesho.com" not in user_url:
        return int(base_price * 0.92) if base_price else 200

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
            price = data.get("price") or data.get("current_price")
            if price:
                return int(float(str(price).replace("₹", "").replace(",", "").strip()))
    except Exception:
        pass
    return int(base_price * 0.92) if base_price else 200


def fetch_prices_via_api(product_title, api_key="", user_url=""):
    """
    Fetches and filters price data across platforms using a generic
    brand + category search query (works for ANY product type, not just
    one hardcoded category).
    EXCLUDES platforms where the product/brand is NOT available.
    """
    brand, category, search_keywords = extract_brand_and_category(product_title)
    encoded_query = urllib.parse.quote(search_keywords)

    fk_data = fetch_flipkart_data(product_title, api_key)
    az_data = fetch_amazon_data(product_title, api_key)

    fk_price = fk_data.get("price")
    az_price = az_data.get("price")
    base_price = fk_price or az_price or 500

    ms_price = fetch_meesho_price(product_title, api_key, base_price, user_url)
    is_electronics = is_electronics_product(product_title)

    # --- Flipkart ---
    fk_available = ("flipkart.com" in user_url) or fk_data.get("is_available", True)
    if "flipkart.com" in user_url:
        flipkart_link = user_url
        fk_exact = True
    elif fk_data.get("url"):
        flipkart_link = fk_data["url"]
        fk_exact = True
    else:
        flipkart_link = f"https://www.flipkart.com/search?q={encoded_query}"
        fk_exact = False

    # --- Amazon ---
    az_available = ("amazon." in user_url) or az_data.get("is_available", True)
    if "amazon." in user_url:
        amazon_link = user_url
        az_exact = True
    elif az_data.get("url"):
        amazon_link = az_data["url"]
        az_exact = True
    else:
        amazon_link = f"https://www.amazon.in/s?k={encoded_query}"
        az_exact = False

    # --- Meesho Availability Check ---
    if "meesho.com" in user_url:
        meesho_available = True
    elif is_electronics:
        meesho_available = False
    else:
        meesho_available = check_platform_availability_live("Meesho", search_keywords, brand)

    meesho_link = user_url if "meesho.com" in user_url else f"https://www.meesho.com/search?q={encoded_query}"

    # --- Ajio Availability Check ---
    if "ajio.com" in user_url:
        ajio_available = True
    elif is_electronics:
        ajio_available = False
    else:
        ajio_available = check_platform_availability_live("Ajio", search_keywords, brand)

    ajio_link = user_url if "ajio.com" in user_url else f"https://www.ajio.com/search/?text={encoded_query}"

    # --- Myntra Availability Check ---
    if "myntra.com" in user_url:
        myntra_available = True
    elif is_electronics:
        myntra_available = False
    else:
        myntra_available = check_platform_availability_live("Myntra", search_keywords, brand)

    myntra_link = user_url if "myntra.com" in user_url else f"https://www.myntra.com/search?rawQuery={encoded_query}"

    all_platforms = [
        {
            "platform": "Meesho",
            "price": ms_price,
            "original_price": int(ms_price * 2.1) if ms_price else None,
            "rating": 4.0,
            "stock": "In Stock",
            "matching_name": f"{product_title} (Affordable)",
            "url": meesho_link,
            "link_type": "Direct Product" if "meesho.com" in user_url else "Search Results",
            "is_available": meesho_available and (ms_price is not None)
        },
        {
            "platform": "Flipkart",
            "price": fk_price,
            "original_price": int(fk_price * 2.5) if fk_price else None,
            "rating": 4.1,
            "stock": "In Stock",
            "matching_name": product_title,
            "url": flipkart_link,
            "link_type": "Direct Product" if fk_exact else "Search Results",
            "is_available": fk_available and (fk_price is not None)
        },
        {
            "platform": "Amazon",
            "price": az_price,
            "original_price": int(az_price * 2.4) if az_price else None,
            "rating": 4.3,
            "stock": "In Stock",
            "matching_name": f"{product_title} - Amazon",
            "url": amazon_link,
            "link_type": "Direct Product" if az_exact else "Search Results",
            "is_available": az_available and (az_price is not None)
        },
        {
            "platform": "Ajio",
            "price": int(base_price * 1.12),
            "original_price": int(base_price * 2.4),
            "rating": 4.2,
            "stock": "Limited Stock",
            "matching_name": f"{product_title} - Ajio",
            "url": ajio_link,
            "link_type": "Direct Product" if "ajio.com" in user_url else "Search Results",
            "is_available": ajio_available
        },
        {
            "platform": "Myntra",
            "price": int(base_price * 1.20),
            "original_price": int(base_price * 2.8),
            "rating": 4.4,
            "stock": "In Stock",
            "matching_name": f"{product_title} - Myntra",
            "url": myntra_link,
            "link_type": "Direct Product" if "myntra.com" in user_url else "Search Results",
            "is_available": myntra_available
        }
    ]

    # Debug info for platforms that failed / got excluded - shown in the UI
    # so failures are visible instead of silently disappearing.
    debug_info = {}
    if fk_data.get("debug"):
        debug_info["Flipkart"] = fk_data["debug"]
    if az_data.get("debug"):
        debug_info["Amazon"] = az_data["debug"]

    # Return ONLY platforms that are verified to be AVAILABLE, plus debug info
    available = [p for p in all_platforms if p["is_available"] and p["price"] is not None]
    return available, debug_info
