import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_NAME = "database.db"
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    
    # Пользователи
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # Администраторы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )""")
    # Категории
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )""")
    
    # Товары
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER REFERENCES categories(category_id),
        description TEXT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        is_available BOOLEAN DEFAULT TRUE
    )""")
    
    # Фото товаров
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product_images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(product_id),
        image_path TEXT NOT NULL,
        is_main BOOLEAN DEFAULT FALSE
    )""")
    
    # Размеры и наличие (исправленная версия)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sizes (
        size_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(product_id),
        size_value TEXT NOT NULL,  -- 'S', 'M', 'L' или цифры
        quantity INTEGER DEFAULT 0,
        UNIQUE(product_id, size_value)
    )""")
    
    # Корзина
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(user_id),
        product_id INTEGER REFERENCES products(product_id),
        size_id INTEGER REFERENCES sizes(size_id),
        quantity INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Заказы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(user_id),
        status TEXT DEFAULT 'new',  -- new, paid, shipped, delivered, cancelled
        total_amount REAL NOT NULL,
        delivery_address TEXT,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    )""")
    
    # Состав заказа
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER REFERENCES orders(order_id),
        product_id INTEGER REFERENCES products(product_id),
        size_id INTEGER REFERENCES sizes(size_id),
        quantity INTEGER NOT NULL,
        price_at_order REAL NOT NULL
    )""")
    
    conn.commit()
    conn.close()
def add_user(user_id,username):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username,registration_date) VALUES (?, ?, ?)", (user_id,username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    a = c.fetchone()
    conn.commit()
    conn.close()
    return a
def get_admin(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    a = c.fetchone()
    conn.commit()
    conn.close()
    return a
def get_all_admins():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    a = list(c.fetchall())
    conn.commit()
    conn.close()
    return a