from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse,HTMLResponse
import uvicorn
import sqlite3
from utility.database import *
from os import getenv
from dotenv import load_dotenv, find_dotenv
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

# Конфигурация
load_dotenv(find_dotenv())
ADMIN_TOKEN = getenv('ADMIN_TOKEN')
LOCALTONET_URL = getenv('LOCALTONET_URL')


def run_admin_panel():
    # Запуск Localtonet
    import subprocess
    localtonet = subprocess.Popen(["localtonet", "--port", "8000"], stdout=subprocess.PIPE)
    
    # Запуск FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/")
async def home(request: Request):    
    return RedirectResponse(f"/admin")
    
@app.get("/admin")
async def admin_interface(request: Request):
    with open("admin/templates/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# API Endpoints
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
    item = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,)).fetchone()
    conn.close()
    
    if not item:
        raise HTTPException(status_code=404)
    
    return dict(item)

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

@app.put("/api/{table}/{id}")
async def update_item(table: str, id: int, request: Request):
    data = await request.json()
    conn = get_db()
    
    set_clause = ', '.join([f"{key} = ?" for key in data])
    values = list(data.values()) + [id]
    
    conn.execute(
        f"UPDATE {table} SET {set_clause} WHERE id = ?",
        values
    )
    conn.commit()
    conn.close()
    
    return {"status": "updated"}

@app.delete("/api/{table}/{id}")
async def delete_item(table: str, id: int):
    conn = get_db()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return {"status": "deleted"}

