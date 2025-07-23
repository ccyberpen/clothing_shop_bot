import sqlite3
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
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def get_product(product_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, SUM(s.quantity) as total_quantity 
        FROM products p
        LEFT JOIN sizes s ON p.product_id = s.product_id
        WHERE p.product_id = ?
        GROUP BY p.product_id
    """, (product_id,))
    return cur.fetchone()

def get_product_images(product_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM product_images 
        WHERE product_id = ?
        ORDER BY is_main DESC
    """, (product_id,))
    return cur.fetchall()

def get_categories(parent_id=None):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if parent_id is None:
        # Явно проверяем NULL и пустые значения
        cur.execute("""
            SELECT * FROM categories 
            WHERE parent_id IS NULL 
               OR parent_id = ''
               OR TRIM(parent_id) = ''
        """)
    else:
        # Для подкатегорий проверяем точное соответствие
        cur.execute("""
            SELECT * FROM categories 
            WHERE parent_id = ?
        """, (str(parent_id),))
    
    result = cur.fetchall()
    conn.close()
    return result

def get_products(category_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, SUM(s.quantity) as total_quantity 
        FROM products p
        LEFT JOIN sizes s ON p.product_id = s.product_id
        WHERE p.category_id = ? AND p.is_available = 1
        GROUP BY p.product_id
    """, (category_id,))
    result = cur.fetchall()
    conn.close()
    return result
def get_product_sizes(product_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM sizes 
        WHERE product_id = ? AND quantity > 0
        ORDER BY size_value
    """, (product_id,))
    sizes = cur.fetchall()
    conn.close()
    return sizes

def add_to_cart_db(user_id: int, product_id: int, size_id: int = None):
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    
    try:
        # Проверяем, есть ли уже такой товар в корзине
        if size_id:
            cur.execute("""
                SELECT cart_id, quantity FROM cart 
                WHERE user_id = ? AND product_id = ? AND size_id = ?
            """, (user_id, product_id, size_id))
        else:
            cur.execute("""
                SELECT cart_id, quantity FROM cart 
                WHERE user_id = ? AND product_id = ? AND size_id IS NULL
            """, (user_id, product_id))
        
        existing = cur.fetchone()
        
        if existing:
            # Увеличиваем количество, если товар уже в корзине
            new_quantity = existing[1] + 1
            cur.execute("""
                UPDATE cart SET quantity = ? 
                WHERE cart_id = ?
            """, (new_quantity, existing[0]))
        else:
            # Добавляем новый товар в корзину
            cur.execute("""
                INSERT INTO cart (user_id, product_id, size_id, quantity) 
                VALUES (?, ?, ?, 1)
            """, (user_id, product_id, size_id))
        
        conn.commit()
    finally:
        conn.close()
def get_product_total_quantity(product_id: int) -> int:
    """Получает общее количество товара (без учета размеров)"""
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT SUM(quantity) FROM sizes 
        WHERE product_id = ?
    """, (product_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result and result[0] else 0

def get_size_info(size_id: int) -> dict:
    """Получает информацию о размере"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT size_id, size_value, quantity 
        FROM sizes WHERE size_id = ?
    """, (size_id,))
    result = cur.fetchone()
    conn.close()
    return dict(result) if result else None

def check_product_in_cart(user_id: int, product_id: int, size_id: int = None) -> int:
    """Проверяет количество товара в корзине пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    
    if size_id:
        cur.execute("""
            SELECT SUM(quantity) FROM cart 
            WHERE user_id = ? AND product_id = ? AND size_id = ?
        """, (user_id, product_id, size_id))
    else:
        cur.execute("""
            SELECT SUM(quantity) FROM cart 
            WHERE user_id = ? AND product_id = ? AND size_id IS NULL
        """, (user_id, product_id))
    
    result = cur.fetchone()
    conn.close()
    return result[0] if result and result[0] else 0
def get_cart_items(user_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            c.cart_id, c.quantity,
            p.product_id, p.name, p.price,
            s.size_id, s.size_value
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        LEFT JOIN sizes s ON c.size_id = s.size_id
        WHERE c.user_id = ?
    """, (user_id,))
    items = cur.fetchall()
    conn.close()
    return [dict(item) for item in items]

def create_order(user_id: int, contact_info: str) -> int:
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    
    try:
        # Получаем содержимое корзины
        cart_items = get_cart_items(user_id)
        if not cart_items:
            raise ValueError("Корзина пуста")
        
        # Рассчитываем общую сумму
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Создаем заказ
        cur.execute("""
            INSERT INTO orders (user_id, total_amount, phone, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, total_amount, contact_info, "processing"))
        order_id = cur.lastrowid
        
        # Добавляем товары в заказ
        for item in cart_items:
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, size_id, quantity, price_at_order)
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, item['product_id'], item.get('size_id'), item['quantity'], item['price']))
        
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_order_total(order_id: int) -> float:
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Получаем сумму заказа из таблицы orders
        cur.execute("""
            SELECT total_amount 
            FROM orders 
            WHERE order_id = ?
        """, (order_id,))
        
        result = cur.fetchone()
        if not result:
            raise ValueError("Заказ не найден")
        
        # Возвращаем сумму, округленную до 2 знаков
        return round(float(result['total_amount']), 2)
        
    except Exception as e:
        print(f"Ошибка получения суммы заказа: {e}")
        raise
    finally:
        conn.close()

def clear_cart(user_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
# Добавляем функцию для обновления остатков
def update_inventory(order_id: int, decrease: bool = True):
    """Обновление остатков товаров при изменении статуса заказа"""
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        # Получаем все товары из заказа
        items = conn.execute("""
            SELECT product_id, size_id, quantity 
            FROM order_items 
            WHERE order_id = ?
        """, (order_id,)).fetchall()
        
        for item in items:
            if item['size_id']:
                # Для товаров с размерами обновляем конкретный размер
                conn.execute("""
                    UPDATE sizes 
                    SET quantity = quantity + ? 
                    WHERE size_id = ?
                """, (-item['quantity'] if decrease else item['quantity'], item['size_id']))
            else:
                # Для товаров без размеров обновляем общее количество
                conn.execute("""
                    UPDATE products 
                    SET quantity = quantity + ? 
                    WHERE product_id = ?
                """, (-item['quantity'] if decrease else item['quantity'], item['product_id']))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
def get_user_orders(user_id: int) -> list:
    """Получаем список заказов пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, status, total_amount, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        return cur.fetchall()
    except Exception as e:
        print(f"Ошибка при получении заказов: {e}")
        return []
    finally:
        conn.close()
def get_order_details(order_id: int) -> dict:
    """
    Получает детальную информацию о заказе
    :param order_id: ID заказа
    :return: Словарь с данными заказа или None если заказ не найден
    """
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем основную информацию о заказе
        cur.execute("""
            SELECT 
                order_id,
                user_id,
                status,
                total_amount,
                phone,
                created_at,
                updated_at
            FROM orders
            WHERE order_id = ?
        """, (order_id,))
        
        order = cur.fetchone()
        
        if not order:
            return None
            
        return dict(order)  # Конвертируем Row в dict
        
    except Exception as e:
        print(f"Ошибка при получении деталей заказа: {e}")
        return None
    finally:
        conn.close()


def get_order_items(order_id: int) -> list:
    """
    Получает список товаров в заказе
    :param order_id: ID заказа
    :return: Список словарей с товарами или пустой список
    """
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                oi.item_id,
                oi.product_id,
                oi.size_id,
                oi.quantity,
                oi.price_at_order,
                p.name,
                p.description,
                s.size_value
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.product_id
            LEFT JOIN sizes s ON oi.size_id = s.size_id
            WHERE oi.order_id = ?
            ORDER BY oi.item_id
        """, (order_id,))
        
        items = cur.fetchall()
        return [dict(item) for item in items]
        
    except Exception as e:
        print(f"Ошибка при получении товаров заказа: {e}")
        return []
    finally:
        conn.close()