import aiohttp
import json
import os
from dotenv import load_dotenv
from typing import Optional

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Отправка сообщения через чистый aiohttp"""
    token = os.getenv('TOKEN')
    if not token:
        raise ValueError("Telegram token not configured")
    
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return True
                error = await response.text()
                print(f"Telegram API error: {error}")
                return False
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False