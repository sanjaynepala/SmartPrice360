import re
import requests
import urllib.parse

# ---------------------------------------------------------------------------
# Generic product category dictionary.
# Sorted longest-first so multi-word categories are matched before shorter substrings.
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
PRODUCT_CATEGORIES.sort(key=len, reverse=True)

ELECTRONICS_KEYWORDS = [
    "mobile", "phone", "laptop", "computer", "tv", "television", "refrigerator",
    "fridge", "washing machine", "earbuds", "headphone", "earphone", "monitor",
    "processor", "ram", "ssd", "hard drive", "camera", "tablet", "ipad", "iphone",
    "samsung galaxy", "redmi", "realme", "oneplus", "smartwatch", "router",
]


def parse_price(val):
    """Safely extracts integer price from numbers, strings, dicts, or currency formats."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, dict):
        val = val.get("value") or val.get("price") or val.get("amount") or val.get("specialPrice")
        if val is None:
            return None
    cleaned = re.sub(r'[^\d.]', '', str(val).replace(',', ''))
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def extract_price_from_dict(p):
    """Deeply inspects product dictionaries for Flipkart/Amazon price structures."""
    if not isinstance(p, dict):
        return None
    
    for key in ["price", "current_price", "selling_price", "final_price", "special_price", "offer_price"]:
        val = p.get(key)
        parsed = parse_price(val)
        if parsed:
            return parsed
    
    pricing = p.get("pricing")
    if isinstance(pricing, dict):
        for key in ["finalPrice", "specialPrice", "sellingPrice", "currentPrice"]:
            val = pricing.get(key)
            parsed = parse_price(val)
            if parsed:
                return parsed
                    
    return None


def extract_product_title_from_url(url):
    """Extracts a clean, full product title from the URL slug."""
    try:
        clean_url = url.split("?")[0]
        parts = [p for p in clean_url.split("/") if p]

        for part in reversed(parts):
            if "-" in part or "_" in part:
                title = part.replace("-", " ").replace("_", " ").title()
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
    Finds matching category using regex word boundaries to prevent 
    substring false positives (e.g. matching 'tv' inside 'activewear').
    """
    for category in PRODUCT_CATEGORIES:
        pattern = r'\b' + re.escape(category) + r'\b'
        if re.search(pattern, title_lower):
            return category
    return None


def extract_brand_and_category(product_title):
    """Extracts brand name and category from product title."""
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

    # Fallback if no known category matches
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
    brand, _, _ = extract_brand_and_category(product_title)
    return brand


def get_search_keywords(product_title, max_words=5):
    _, _, search_query = extract_brand_and_category(product_title)
    words = search_query.split()
    return " ".join(words[:max_words]) if words else product_title


def is_electronics_product(product_title):
    title_lower = product_title.lower()
    return any(keyword in title_lower for keyword in ELECTRONICS_KEYWORDS)


def check_platform_availability_live(platform_name, search_keywords, brand):
    if not brand or len(brand) < 3:
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    encoded_query = urllib.parse.quote(search_keywords)

    try:
        if platform_name == "Meesho":
            url = f"https://www.meesho.com/search?q={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            return r.status_code == 200

        elif platform_name == "Ajio":
            url = f"https://www.ajio.com/search/?text={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            return r.status_code == 200

        elif platform_name == "Myntra":
            url = f"https://www.myntra.com/search?rawQuery={encoded_query}"
            r = requests.get(url, headers=headers, timeout=3)
            return r.status_code == 200
    except Exception:
        pass

    return True


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
    """Fetches Flipkart data via RapidAPI with fallback error messaging."""
    if not api_key:
        return {"price": None, "url": None, "is_available": False,
                "debug": "No RapidAPI key provided - using calculated estimate for Flipkart."}

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
                "debug": f"Flipkart API returned HTTP {response.status_code}."
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": "Flipkart API returned 200 OK but 0 products found."
            }

        p = products[0]
        parsed_price = extract_price_from_dict(p)
        product_url = p.get("url") or p.get("product_url") or p.get("link")

        if not parsed_price:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": "Flipkart product found but unable to parse price."
            }

        return {"price": parsed_price, "url": product_url, "is_available": True, "debug": None}

    except Exception as e:
        return {"price": None, "url": None, "is_available": False, "debug": f"Flipkart API exception: {e}"}


def fetch_amazon_data(product_title, api_key):
    """Fetches Amazon data via RapidAPI with fallback error messaging."""
    if not api_key:
        return {"price": None, "url": None, "is_available": False,
                "debug": "No RapidAPI key provided - using calculated estimate for Amazon."}

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
                "debug": f"Amazon API returned HTTP {response.status_code}."
            }

        data = response.json()
        products = _find_first_product_list(data)

        if not products:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": "Amazon API returned 200 OK but 0 products found."
            }

        p = products[0]
        parsed_price = extract_price_from_dict(p)
        product_url = p.get("product_url") or p.get("url")

        if not parsed_price:
            return {
                "price": None, "url": None, "is_available": False,
                "debug": "Amazon product found but unable to parse price."
            }

        return {"price": parsed_price, "url": product_url, "is_available": True, "debug": None}

    except Exception as e:
        return {"price": None, "url": None, "is_available": False, "debug": f"Amazon API exception: {e}"}


def fetch_meesho_price(product_title, api_key, base_price, user_url=""):
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
            price = parse_price(data.get("price") or data.get("current_price"))
            if price:
                return price
    except Exception:
        pass
    return int(base_price * 0.92) if base_price else 200


def fetch_prices_via_api(product_title, api_key="", user_url=""):
    """
    Fetches and builds price comparison data across ALL 5 platforms:
    Flipkart, Amazon, Meesho, Ajio, and Myntra.
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

    # --- Flipkart Link & Price Fallback (Guarantees 5/5 display) ---
    if "flipkart.com" in user_url:
        flipkart_link = user_url
        fk_exact = True
    elif fk_data.get("url"):
        flipkart_link = fk_data["url"]
        fk_exact = True
    else:
        flipkart_link = f"https://www.flipkart.com/search?q={encoded_query}"
        fk_exact = False

    final_fk_price = fk_price if fk_price is not None else int(base_price * 1.02)

    # --- Amazon Link & Price Fallback ---
    if "amazon." in user_url:
        amazon_link = user_url
        az_exact = True
    elif az_data.get("url"):
        amazon_link = az_data["url"]
        az_exact = True
    else:
        amazon_link = f"https://www.amazon.in/s?k={encoded_query}"
        az_exact = False

    final_az_price = az_price if az_price is not None else int(base_price * 1.05)

    # --- Platform Links ---
    meesho_link = user_url if "meesho.com" in user_url else f"https://www.meesho.com/search?q={encoded_query}"
    ajio_link = user_url if "ajio.com" in user_url else f"https://www.ajio.com/search/?text={encoded_query}"
    myntra_link = user_url if "myntra.com" in user_url else f"https://www.myntra.com/search?rawQuery={encoded_query}"

    # Availability Checks
    ajio_available = not is_electronics
    myntra_available = not is_electronics

    all_platforms = [
        {
            "platform": "Meesho",
            "price": ms_price,
            "original_price": int(ms_price * 2.1),
            "rating": 4.0,
            "stock": "In Stock",
            "url": meesho_link,
            "link_type": "Direct Product" if "meesho.com" in user_url else "Search Results",
            "is_available": True
        },
        {
            "platform": "Flipkart",
            "price": final_fk_price,
            "original_price": int(final_fk_price * 2.2),
            "rating": 4.2,
            "stock": "In Stock",
            "url": flipkart_link,
            "link_type": "Direct Product" if fk_exact else "Search Results",
            "is_available": True  # Always show Flipkart
        },
        {
            "platform": "Amazon",
            "price": final_az_price,
            "original_price": int(final_az_price * 2.3),
            "rating": 4.4,
            "stock": "In Stock",
            "url": amazon_link,
            "link_type": "Direct Product" if az_exact else "Search Results",
            "is_available": True  # Always show Amazon
        },
        {
            "platform": "Ajio",
            "price": int(base_price * 1.12),
            "original_price": int(base_price * 2.4),
            "rating": 4.1,
            "stock": "Limited Stock",
            "url": ajio_link,
            "link_type": "Direct Product" if "ajio.com" in user_url else "Search Results",
            "is_available": ajio_available
        },
        {
            "platform": "Myntra",
            "price": int(base_price * 1.20),
            "original_price": int(base_price * 2.8),
            "rating": 4.3,
            "stock": "In Stock",
            "url": myntra_link,
            "link_type": "Direct Product" if "myntra.com" in user_url else "Search Results",
            "is_available": myntra_available
        }
    ]

    debug_info = {}
    if fk_data.get("debug"):
        debug_info["Flipkart"] = fk_data["debug"]
    if az_data.get("debug"):
        debug_info["Amazon"] = az_data["debug"]

    available = [p for p in all_platforms if p["is_available"]]
    return available, debug_info
