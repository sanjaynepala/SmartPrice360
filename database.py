import sqlite3

def init_db():
    """Initializes SQLite database and creates price_history table if it doesn't exist."""
    try:
        conn = sqlite3.connect("prices.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_title TEXT,
                platform TEXT,
                price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization error: {e}")

def save_price(product_title, platform, price):
    """Saves a price record to the database."""
    try:
        conn = sqlite3.connect("prices.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO price_history (product_title, platform, price) VALUES (?, ?, ?)",
            (product_title, platform, price)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving price to database: {e}")

def get_price_history(product_title):
    """Retrieves price history records for a given product title."""
    try:
        conn = sqlite3.connect("prices.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT platform, price, timestamp FROM price_history WHERE product_title = ? ORDER BY timestamp ASC", 
            (product_title,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error fetching price history: {e}")
        return []
