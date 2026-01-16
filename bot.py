import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv
from publisher import publish_post

load_dotenv()

# Состояния диалога
URL, CURRENT_PRICE, OLD_PRICE, RATING, PROMOCODE, PROMO_DESC, PROMO_DATE = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Кидай рефералку.")
    return URL

async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("Пожалуйста, отправьте корректную ссылку.")
        return URL
    context.user_data["url"] = url

    # Попробуем извлечь название
    title = "Товар"
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0..."})
        soup = BeautifulSoup(resp.text, "lxml")
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    except:
        pass

    context.user_data["title"] = title
    await update.message.reply_text(f"Название: {title}\n\nВведите текущую цену (в ₽):")
    return CURRENT_PRICE

async def receive_current_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(" ", ""))
        context.user_data["current_price"] = price
        await update.message.reply_text("Введите старую цену (в ₽):")
        return OLD_PRICE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return CURRENT_PRICE

async def receive_old_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(" ", ""))
        context.user_data["old_price"] = price
        await update.message.reply_text("Введите рейтинг (например, 4.8):")
        return RATING
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return OLD_PRICE

async def receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rating = update.message.text.strip()
    context.user_data["rating"] = rating
    await update.message.reply_text("Введи промокод. Если нет — напишите «нет».")
    return PROMOCODE

async def receive_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo = update.message.text.strip()
    if promo.lower() in ("нет", "no", "-", "н", "0"):
        context.user_data["promocode"] = None
        context.user_data["promo_desc"] = None
        context.user_data["promo_date"] = None
        return await show_preview(update, context)
    else:
        context.user_data["promocode"] = promo
        await update.message.reply_text("Что даёт промокод? (например: «Скидка 500 ₽»)")
        return PROMO_DESC

async def receive_promo_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["promo_desc"] = update.message.text.strip()
    await update.message.reply_text("До какого числа действует? (например: «20 января»)")
    return PROMO_DATE

async def receive_promo_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["promo_date"] = update.message.text.strip()
    return await show_preview(update, context)

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    old_f = f"{data['old_price']:,}".replace(",", " ")
    current_f = f"{data['current_price']:,}".replace(",", " ")
    discount = round((1 - data["current_price"] / data["old_price"]) * 100) if data["old_price"] > data["current_price"] else 0

    preview = f"""Предпросмотр поста:

🔥 <b>{data['title']}</b>
💰 <s>{old_f} ₽</s> → <b>{current_f} ₽</b>
📉 Выгода {discount}%
⭐ Рейтинг: {data['rating']}
"""

    if data.get("promocode"):
        preview += f"🎁 {data['promo_desc']} до {data['promo_date']}\n🔑 Промокод: [скрыт]"
    else:
        preview += "🎁 Без промокода"

    keyboard = [[InlineKeyboardButton("✅ Опубликовать", callback_data="publish")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(preview, reply_markup=reply_markup, parse_mode="HTML")
    return ConversationHandler.END

async def publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data
    success = publish_post(
        title=data["title"],
        current_price=data["current_price"],
        old_price=data["old_price"],
        rating=data["rating"],
        product_url=data["url"],
        ref_clid="-1003575803799",  # ID канала
        promocode=data.get("promocode"),
        promo_desc=data.get("promo_desc"),
        promo_date=data.get("promo_date")
    )

    if success:
        await query.edit_message_text("✅ Пост опубликован!\n\nКидай новую ссылку.")
    else:
        await query.edit_message_text("❌ Ошибка при публикации.")

    # ❗ Важно: НЕ возвращаемся в URL — оставляем диалог завершённым
    # Пользователь сам отправит новую ссылку или /start

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена. Пришлите ссылку на товар.")
    return URL

def main():
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
            CURRENT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_current_price)],
            OLD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_old_price)],
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rating)],
            PROMOCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promocode)],
            PROMO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_desc)],
            PROMO_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True  # ← позволяет начинать заново без /start
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(publish_callback, pattern="^publish$"))

    application.run_polling()

if __name__ == "__main__":
    main()