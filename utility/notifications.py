import sqlite3
from .telegram_sender import send_telegram_message

async def notify_user(order_id: int, new_status: str) -> bool:
    """Уведомление пользователя через прямое API"""
    conn = None
    try:
        # Получаем данные пользователя
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM orders WHERE order_id = ?", (order_id,))
        order = cur.fetchone()
        
        if not order:
            print(f"Order {order_id} not found")
            return False

        # Формируем текст
        messages = {
            'new': "🆕 Ваш заказ #{} принят в обработку",
            'processing': "🔄 Ваш заказ #{} обрабатывается",
            'completed': "✅ Ваш заказ #{} завершен",
            'cancelled': "❌ Ваш заказ #{} отменен"
        }
        text = messages.get(new_status, f"ℹ️ Статус заказа #{order_id} изменен").format(order_id)
        
        # Отправляем через прямое API
        return await send_telegram_message(order['user_id'], text)
        
    except Exception as e:
        print(f"Notification error: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()