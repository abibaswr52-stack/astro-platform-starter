import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- НАСТРОЙКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Магазин звезд запущен!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- ЛОГИКА БОТА ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Данные о товарах (можно менять цены и названия здесь)
STARS_PACKS = {
    "pack_1": {"name": "⭐ 50 Звёзд", "price": "149₽", "desc": "Стартовый набор для новичков"},
    "pack_2": {"name": "🌟 500 Звёзд", "price": "990₽", "desc": "Популярный выбор среди игроков"},
    "pack_3": {"name": "✨ 1000 Звёзд", "price": "1850₽", "desc": "Выгодный набор для профи"},
    "pack_4": {"name": "👑 5000 Звёзд", "price": "7900₽", "desc": "Ультимативный набор чемпиона"}
}

# Главное меню
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_shop = types.InlineKeyboardButton("🛒 Перейти в магазин", callback_data="open_shop")
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_help = types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    markup.add(btn_shop, btn_profile, btn_help)
    return markup

# Меню магазина
def shop_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(item['name'], callback_data=key) for key, item in STARS_PACKS.items()]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"<b>Привет, {message.from_user.first_name}!</b>\n\nДобро пожаловать в официальный магазин звёзд. Здесь ты можешь мгновенно пополнить свой баланс.",
        parse_mode='HTML',
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Открытие магазина
    if call.data == "open_shop":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="<b>Выберите подходящий пакет звёзд:</b>",
            parse_mode='HTML',
            reply_markup=shop_menu()
        )

    # Возврат в главное меню
    elif call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"<b>Главное меню</b>\n\nВыбери нужный раздел:",
            parse_mode='HTML',
            reply_markup=main_menu()
        )

    # Выбор конкретного товара
    elif call.data in STARS_PACKS:
        item = STARS_PACKS[call.data]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"💳 Купить за {item['price']}", url="https://t.me/your_payment_link")) # Ссылка на оплату
        markup.add(types.InlineKeyboardButton("⬅️ К списку товаров", callback_data="open_shop"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"<b>Товар:</b> {item['name']}\n<b>Описание:</b> {item['desc']}\n\n<b>Цена: {item['price']}</b>",
            parse_mode='HTML',
            reply_markup=markup
        )

if __name__ == "__main__":
    bot.infinity_polling()
