import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def publish_post(title, current_price, old_price, rating, product_url, ref_clid="твой_clid", promocode=None, promo_desc=None, promo_date=None):
    # Реферальная ссылка
    if "?" in product_url:
        ref_url = f"{product_url}&clid={ref_clid}"
    else:
        ref_url = f"{product_url}?clid={ref_clid}"

    # Форматируем цены с пробелами
    old_f = f"{old_price:,}".replace(",", " ")
    current_f = f"{current_price:,}".replace(",", " ")

    # Скидка
    discount = round((1 - current_price / old_price) * 100) if old_price > current_price else 0

    # Основной текст
    caption = f"""🔥 <b>{title}</b>
💰 <s>{old_f} ₽</s> → <b>{current_f} ₽</b>
📉 Выгода {discount}%
⭐ Рейтинг: {rating}
"""

    # Промокод
    if promocode:
        caption += f"🎁 {promo_desc} ₽ до {promo_date}\n"
        caption += f"🔑 По промокоду: <tg-spoiler>{promocode}</tg-spoiler>\n"
    else:
        caption += "\n"

    caption += f'🛍 <a href="{ref_url}">Ссылка на товар</a>'

    # Отправка
    image_url = None
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0..."})
        soup = BeautifulSoup(resp.text, "lxml")
        og = soup.find("meta", property="og:image")
        if og:
            image_url = og["content"]
    except:
        pass

    method = "sendPhoto" if image_url else "sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption" if image_url else "text": caption,
        "photo" if image_url else "text": image_url or caption,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, data=payload)
    return response.ok