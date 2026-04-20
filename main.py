import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. НАСТРОЙКА ДЛЯ RENDER (АНТИ-СОН) ---
app = Flask('')
@app.route('/')
def home(): return "Магазин звезд активен!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ БОТА ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# НАСТРОЙКИ
ADMIN_ID = 1411441331 
ADMIN_USERNAME = "@nebulkin"

# ЦЕНЫ (100 = 18к + ОПТОВЫЕ СКИДКИ)
STARS_PACKS = {
    "p100": {"name": "100 шт.", "price": "18,000 UZS", "desc": "Базовый пакет"},
    "p150": {"name": "150 шт.", "price": "26,500 UZS", "desc": "Экономия при покупке"},
    "p200": {"name": "200 шт.", "price": "34,000 UZS", "desc": "Выгодная цена"},
    "p250": {"name": "250 шт.", "price": "41,500 UZS", "desc": "Хорошая скидка"},
    "p300": {"name": "300 шт.", "price": "48,000 UZS", "desc": "Большая скидка"},
    "p350": {"name": "350 шт.", "price": "55,000 UZS", "desc": "Еще дешевле за 100 шт."},
    "p400": {"name": "400 шт.", "price": "61,000 UZS", "desc": "Оптовая цена"},
    "p450": {"name": "450 шт.", "price": "68,000 UZS", "desc": "Очень выгодно"},
    "p500": {"name": "500 шт.", "price": "75,000 UZS", "desc": "🔥 МАКСИМАЛЬНАЯ ВЫГОДА"}
}

# --- 3. КЛАВИАТУРЫ ---
def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин звёзд", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def shop_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Одинаковые стикеры звезд на кнопках
    btns = [types.InlineKeyboardButton(f"⭐ {k[1:]} — {v['price']}", callback_data=k) for k, v in STARS_PACKS.items()]
    markup.add(*btns)
    markup.row(types.InlineKeyboardButton("💎 СВОЯ СУММА (100 = 18к)", callback_data="custom_amount"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="main_menu"))
    return markup

# --- 4. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"<b>Привет, {message.from_user.first_name}!</b>\nДобро пожаловать в магазин звёзд.",
        parse_mode='HTML',
        reply_markup=main_menu(message.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    try:
        if call.data == "main_menu":
            bot.edit_message_text("<b>Главное меню:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=main_menu(uid))

        elif call.data == "open_shop":
            bot.edit_message_text("<b>Выберите количество звёзд:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=shop_menu())

        elif call.data == "profile":
            text = f"<b>👤 Профиль</b>\n\n<b>Имя:</b> {call.from_user.first_name}\n<b>ID:</b> <code>{uid}</code>\n<b>Баланс:</b> 0 ⭐"
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "help":
            text = f"<b>❓ Поддержка</b>\n\nЕсть вопросы по оплате или заказу?\nНапишите нашему админу:"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👨‍💻 Админ @yngsafar", url=f"https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "custom_amount":
            text = (
                "<b>💎 Индивидуальный заказ</b>\n\n"
                "Вы можете купить любое количество звёзд!\n\n"
                "🔹 <b>Курс:</b> 100 звёзд = 18,000 UZS\n"
                "🔹 <b>Для крупных сумм — отдельные скидки!</b>\n\n"
                "Напишите админу желаемую сумму:"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✉️ Написать админу", url="https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад в магазин", callback_data="open_shop"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data in STARS_PACKS:
            item = STARS_PACKS[call.data]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💳 Оплатить {item['price']}", url=f"https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад к списку", callback_data="open_shop"))
            bot.edit_message_text(
                f"<b>Вы выбрали: {item['name']}</b>\n"
                f"<i>{item['desc']}</i>\n\n"
                f"<b>💰 К оплате: {item['price']}</b>\n\n"
                f"Для покупки напишите администратору по кнопке ниже:",
                uid, call.message.id, parse_mode='HTML', reply_markup=markup
            )

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
