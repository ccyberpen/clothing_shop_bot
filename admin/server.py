from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
import uvicorn
import sqlite3
import os
from os import getenv
from dotenv import load_dotenv, find_dotenv
import shutil
import uuid
from pathlib import Path
import asyncio
from utility.database import *

app = FastAPI()

# Конфигурация
load_dotenv(find_dotenv())
LOCALTONET_URL = getenv('LOCALTONET_URL')
DATABASE_NAME = "database.db"
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "products"), exist_ok=True)
# Конфигурация путей
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
PRODUCT_IMAGES_DIR = STATIC_DIR / "products"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_id_field(table):
    # Определяем имя поля ID
    id_field = {
        'products': 'product_id',
        'categories': 'category_id',
        'orders': 'order_id',
        'users': 'user_id',
        'admins': 'admin_id',
        'sizes': 'size_id'
    }.get(table, 'id')
    return id_field

def run_admin_panel():
    # Запуск Localtonet
    import subprocess
    localtonet = subprocess.Popen(["localtonet", "--port", "8000"], stdout=subprocess.PIPE)
    
    # Запуск FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)


# API Endpoints
@app.get("/")
async def home(request: Request):    
    return RedirectResponse("/admin")

@app.get("/admin")
async def admin_interface(request: Request):
    try:
        with open(TEMPLATES_DIR / "admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin template not found")

@app.get("/api/{table}")
async def get_table(table: str):
    allowed_tables = ['products', 'categories', 'orders', 'users','admins']
    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table")
    
    conn = get_db()
    data = conn.execute(f"SELECT * FROM {table}").fetchall()
    conn.close()
    
    return [dict(row) for row in data]

@app.get("/api/{table}/{id}")
async def get_item(table: str, id: int):
    conn = get_db()
    item = conn.execute(f"SELECT * FROM {table} WHERE {get_id_field(table)} = ?", (id,)).fetchone()
    conn.close()
    
    if not item:
        raise HTTPException(status_code=404)
    
    return dict(item)

@app.get("/api/products/{product_id}/images")
async def get_product_images(product_id: int):
    conn = get_db()
    images = conn.execute("""
        SELECT * FROM product_images 
        WHERE product_id = ?
        ORDER BY is_main DESC
    """, (product_id,)).fetchall()
    conn.close()
    
    return [{
        **dict(img),
        "image_path": f"/static/products/{img['image_path']}"
    } for img in images]

@app.post("/api/products")
async def create_product(
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    description: str = Form(None),
    is_available: bool = Form(True),
    images: list[UploadFile] = File(None)
):
    conn = get_db()
    try:
        # Создаем товар
        cur = conn.execute("""
            INSERT INTO products (name, price, category_id, description, is_available)
            VALUES (?, ?, ?, ?, ?)
        """, [name, price, category_id, description, is_available])
        product_id = cur.lastrowid
        
        # Сохраняем изображения
        if images:
            for img in images:
                if img.content_type.startswith('image/'):
                    filename = f"{uuid.uuid4().hex}{os.path.splitext(img.filename)[1]}"
                    filepath = os.path.join(STATIC_DIR, "products", filename)
                    
                    with open(filepath, "wb") as buffer:
                        shutil.copyfileobj(img.file, buffer)
                    
                    # Первое изображение делаем главным
                    is_main = True if img == images[0] else False
                    
                    conn.execute("""
                        INSERT INTO product_images (product_id, image_path, is_main)
                        VALUES (?, ?, ?)
                    """, [product_id, filename, is_main])
        
        conn.commit()
        return {"product_id": product_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/products/{product_id}")
async def update_product(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    description: str = Form(None),
    is_available: bool = Form(True),
    images: list[UploadFile] = File(None)
):
    conn = get_db()
    try:
        # Обновляем товар
        conn.execute("""
            UPDATE products 
            SET name = ?, price = ?, category_id = ?, description = ?, is_available = ?
            WHERE product_id = ?
        """, [name, price, category_id, description, is_available, product_id])
        
        # Добавляем новые изображения
        if images:
            for img in images:
                if img.content_type.startswith('image/'):
                    filename = f"{uuid.uuid4().hex}{os.path.splitext(img.filename)[1]}"
                    filepath = os.path.join(STATIC_DIR, "products", filename)
                    
                    with open(filepath, "wb") as buffer:
                        shutil.copyfileobj(img.file, buffer)
                    
                    # Новые изображения не главные по умолчанию
                    conn.execute("""
                        INSERT INTO product_images (product_id, image_path, is_main)
                        VALUES (?, ?, ?)
                    """, [product_id, filename, False])
        
        conn.commit()
        return {"status": "updated"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/images/{image_id}")
async def delete_image(image_id: int):
    conn = get_db()
    try:
        # Получаем информацию об изображении
        image = conn.execute("""
            SELECT image_path FROM product_images WHERE image_id = ?
        """, (image_id,)).fetchone()
        
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Удаляем файл
        filepath = os.path.join(STATIC_DIR, "products", image['image_path'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Удаляем запись из БД
        conn.execute("DELETE FROM product_images WHERE image_id = ?", (image_id,))
        conn.commit()
        
        return {"status": "deleted"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/images/{image_id}/set_main")
async def set_main_image(image_id: int):
    conn = get_db()
    try:
        # Получаем product_id изображения
        image = conn.execute("""
            SELECT product_id FROM product_images WHERE image_id = ?
        """, (image_id,)).fetchone()
        
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Сбрасываем все главные изображения для этого товара
        conn.execute("""
            UPDATE product_images 
            SET is_main = FALSE 
            WHERE product_id = ?
        """, (image['product_id'],))
        
        # Устанавливаем текущее как главное
        conn.execute("""
            UPDATE product_images 
            SET is_main = TRUE 
            WHERE image_id = ?
        """, (image_id,))
        
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# Общие CRUD endpoints для других таблиц
@app.post("/api/{table}")
async def create_item(table: str, request: Request):
    data = await request.json()
    conn = get_db()
    cursor = conn.cursor()
    
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    
    cursor.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        list(data.values())
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return {"id": new_id}

@app.put("/api/orders/{order_id}")
async def update_order(
    order_id: int,
    status: str = Form(...),
    phone: str = Form(None)
):
    """Обновление статуса заказа"""
    conn = get_db()
    try:
        # Получаем текущий статус
        cur = conn.cursor()
        cur.execute("SELECT status, user_id FROM orders WHERE order_id = ?", (order_id,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(404, detail="Order not found")
            
        old_status, user_id = result[0], result[1]
        
        # Обновляем запись
        cur.execute("""
            UPDATE orders 
            SET status = ?,
                phone = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (status, phone, order_id))
        conn.commit()
        
        # Отправляем уведомление
        from utility.notifications import notify_user
        await notify_user(order_id, status)
        
        # Обновляем остатки
        if status == 'completed' and old_status != 'completed':
            update_inventory(order_id, decrease=True)
        elif status == 'cancelled' and old_status == 'completed':
            update_inventory(order_id, decrease=False)
            
        return {"status": "success"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/{table}/{id}")
async def update_item(table: str, id: int, request: Request):
    data = await request.json()
    conn = get_db()
    
    set_clause = ', '.join([f"{key} = ?" for key in data])
    values = list(data.values()) + [id]
    
    conn.execute(
        f"UPDATE {table} SET {set_clause} WHERE {get_id_field(table)} = ?",
        values
    )
    conn.commit()
    conn.close()
    
    return {"status": "updated"}

@app.delete("/api/{table}/{item_id}")
async def delete_item(table: str, item_id: int):
    conn = get_db()
    try:
        # Проверяем существование записи
        item = conn.execute(
            f"SELECT * FROM {table} WHERE {get_id_field(table)} = ?",
            (item_id,)
        ).fetchone()
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Запись с ID {item_id} не найдена в таблице {table}"
            )
        # Удаляем связанные данные для товаров
        if table == "products":
            # Удаляем изображения товара
            images = conn.execute(
                "SELECT image_path FROM product_images WHERE product_id = ?",
                (item_id,)
            ).fetchall()
            
            for img in images:
                img_path = Path("static/products") / img["image_path"]
                if img_path.exists():
                    img_path.unlink()
            
            conn.execute(
                "DELETE FROM product_images WHERE product_id = ?",
                (item_id,)
            )
        
        # Удаляем основную запись
        conn.execute(
            f"DELETE FROM {table} WHERE {get_id_field(table)} = ?",
            (item_id,)
        )
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Запись {item_id} из таблицы {table} удалена"
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении: {str(e)}"
        )
    finally:
        conn.close()
@app.get("/api/products/{product_id}/sizes")
async def get_product_sizes(product_id: int):
    conn = get_db()
    sizes = conn.execute("""
        SELECT * FROM sizes 
        WHERE product_id = ?
        ORDER BY size_value
    """, (product_id,)).fetchall()
    conn.close()
    return [dict(size) for size in sizes]

@app.post("/api/products/{product_id}/sizes")
async def add_product_size(
    product_id: int,
    size_value: str = Form(...),
    quantity: int = Form(0)
):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO sizes (product_id, size_value, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id, size_value) 
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, [product_id, size_value, quantity])
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.delete("/api/sizes/{size_id}")
async def delete_size(size_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM sizes WHERE size_id = ?", (size_id,))
        conn.commit()
        return {"status": "deleted"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()
@app.put("/api/sizes/{size_id}")
async def update_size(size_id: int, request: Request):
    data = await request.json()
    conn = get_db()
    try:
        conn.execute("""
            UPDATE sizes 
            SET quantity = ?
            WHERE size_id = ?
        """, [data.get('quantity', 0), size_id])
        conn.commit()
        return {"status": "updated"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@app.get("/api/orders/{order_id}/items")
async def get_order_items(order_id: int):
    conn = get_db()
    try:
        items = conn.execute("""
            SELECT 
                oi.*, 
                p.name,
                p.price as current_price,
                s.size_value
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            LEFT JOIN sizes s ON oi.size_id = s.size_id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()
        
        return [dict(item) for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()