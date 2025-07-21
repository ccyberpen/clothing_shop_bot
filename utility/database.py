import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cur.execute("PRAGMA foreign_keys = ON")
    
    # Пользователи (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Администраторы (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY,
        adminname TEXT
    )""")
    
    # Категории (добавляем parent_id для иерархии)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER REFERENCES categories(category_id)
    )""")
    
    # Товары (добавляем is_available)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER REFERENCES categories(category_id),
        description TEXT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        is_available BOOLEAN DEFAULT TRUE
    )""")
    
    # Фото товаров (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product_images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
        image_path TEXT NOT NULL,
        is_main BOOLEAN DEFAULT FALSE
    )""")
    
    # Размеры и наличие (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sizes (
        size_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
        size_value TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        UNIQUE(product_id, size_value)
    )""")
    
    # Корзина (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(product_id),
        size_id INTEGER REFERENCES sizes(size_id),
        quantity INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Заказы (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(user_id),
        status TEXT DEFAULT 'new',
        total_amount REAL NOT NULL,
        delivery_address TEXT,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    )""")
    
    # Состав заказа (оставляем как есть)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(product_id),
        size_id INTEGER REFERENCES sizes(size_id),
        quantity INTEGER NOT NULL,
        price_at_order REAL NOT NULL
    )""")
    
    # Создаем индексы для ускорения запросов
    cur.execute("CREATE INDEX IF NOT EXISTS idx_product_images ON product_images(product_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_product_category ON products(category_id)")
    
    conn.commit()
    conn.close()

# Ваши существующие функции оставляем без изменений
def add_user(user_id, username):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, username, registration_date) VALUES (?, ?, ?)", 
              (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    a = c.fetchone()
    conn.close()
    return a

def get_admin(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    a = c.fetchone()
    conn.close()
    return a

def get_all_admins():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    a = list(c.fetchall())
    conn.close()
    return a

# Новые функции для работы с изображениями
def add_product_image(product_id, image_path, is_main=False):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    # Если добавляем главное изображение, сбрасываем другие главные
    if is_main:
        c.execute("UPDATE product_images SET is_main = FALSE WHERE product_id = ?", (product_id,))
    
    c.execute("INSERT INTO product_images (product_id, image_path, is_main) VALUES (?, ?, ?)",
              (product_id, image_path, is_main))
    conn.commit()
    conn.close()

def get_product_images(product_id):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM product_images WHERE product_id = ? ORDER BY is_main DESC", (product_id,))
    images = c.fetchall()
    conn.close()
    return [dict(image) for image in images]

def delete_image(image_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM product_images WHERE image_id = ?", (image_id,))
    conn.commit()
    conn.close()

def set_main_image(image_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    # Получаем product_id изображения
    c.execute("SELECT product_id FROM product_images WHERE image_id = ?", (image_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return False
    
    product_id = result[0]
    
    # Сбрасываем все главные изображения для этого товара
    c.execute("UPDATE product_images SET is_main = FALSE WHERE product_id = ?", (product_id,))
    
    # Устанавливаем текущее как главное
    c.execute("UPDATE product_images SET is_main = TRUE WHERE image_id = ?", (image_id,))
    
    conn.commit()
    conn.close()
    return True
