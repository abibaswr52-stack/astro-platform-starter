import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. НАСТРОЙКА ДЛЯ RENDER (АНТИ-СОН) ---
app = Flask('')
@app.route('/')
def home(): return "Магазин звезд активен 24/7!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ БОТА ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Сбрасываем старые соединения, чтобы не было ошибки 409 Conflict
bot.remove_webhook()

# НАСТРОЙКИ
ADMIN_ID = 123456789  # <--- ВСТАВЬ СВОЙ ID СЮДА
ADMIN_USERNAME = "@yngsafar"

# ДАННЫЕ МАГАЗИНА (Твоя сетка цен + ОПТ)
STARS_PACKS = {
    "p100": {"name": "⭐ 100", "price": "18,000 UZS", "desc": "Базовый пакет"},
    "p150": {"name": "⭐ 150", "price": "27,000 UZS", "desc": "Стандартный набор"},
    "p200": {"name": "⭐ 200", "price": "36,000 UZS", "desc": "Больше звезд — больше возможностей"},
    "p250": {"name": "⭐ 250", "price": "40,000 UZS", "desc": "✅ Оптимальный вариант (Скидка!)"},
    "p300": {"name": "⭐ 300", "price": "48,000 UZS", "desc": "🔥 Популярный выбор"},
    "p350": {"name": "⭐ 350", "price": "56,000 UZS", "desc": "Выгоднее, чем поштучно"},
    "p400": {"name": "⭐ 400", "price": "64,000 UZS", "desc": "Оптовая цена"},
    "p450": {"name": "⭐ 450", "price": "72,000 UZS", "desc": "Для продвинутых игроков"},
    "p500": {"name": "⭐ 500", "price": "80,000 UZS", "desc": "💎 Самый выгодный вариант"}
}

# --- 3. КЛАВИАТУРЫ ---

def main_menu_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин звёзд", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def shop_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for k, v in STARS_PACKS.items():
        prefix = ""
        if k == "p250": prefix = "✅ "
        if k == "p300": prefix = "🔥 "
        if k == "p500": prefix = "💎 "
        btns.append(types.InlineKeyboardButton(f"{prefix}{v['name']} — {v['price']}", callback_data=k))
    
    markup.add(*btns)
    markup.row(types.InlineKeyboardButton("✨ СВОЯ СУММА (ОТ 500 ⭐)", callback_data="custom_amount"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="main_menu"))
    return markup

# --- 4. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"<b>Привет, {message.from_user.first_name}!</b>\n\nДобро пожаловать в магазин звёзд. Выберите нужный раздел:",
        parse_mode='HTML',
        reply_markup=main_menu_markup(message.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    try:
        if call.data == "main_menu":
            bot.edit_message_text("<b>Главное меню:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=main_menu_markup(uid))

        elif call.data == "open_shop":
            bot.edit_message_text("<b>Выберите количество звёзд:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=shop_menu_markup())

        elif call.data == "profile":
            text = (
                f"<b>👤 Ваш профиль</b>\n\n"
                f"<b>Имя:</b> {call.from_user.first_name}\n"
                f"<b>Ваш ID:</b> <code>{uid}</code>\n"
                f"<b>Баланс:</b> 0 ⭐\n\n"
                f"<i>История покупок пуста.</i>"
            )
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "help":
            text = f"<b>❓ Поддержка</b>\n\nЕсть вопросы по оплате или получению звёзд?\nНапишите нашему админу:"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👨‍💻 Связаться с @yngsafar", url=f"https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "custom_amount":
            text = (
                "<b>💎 Индивидуальный заказ</b>\n\n"
                "Хотите купить любое другое количество звёзд?\n\n"
                "🔹 <b>Курс:</b> 100 ⭐ = 18,000 UZS\n"
                "🔹 <b>Для крупных сумм (от 500 ⭐)</b> — персональные скидки!\n\n"
                "Напишите админу желаемую сумму:"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✉️ Написать админу", url="https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад в магазин", callback_data="open_shop"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "admin_panel" and uid == ADMIN_ID:
            bot.edit_message_text("<b>🛠 Админ-панель</b>\n\nБот работает в штатном режиме.", uid, call.message.id, parse_mode='HTML', 
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))

        elif call.data in STARS_PACKS:
            item = STARS_PACKS[call.data]
            tag = ""
            if call.data == "p250": tag = "\n\n📍 <b>Статус: Оптимальный вариант</b>"
            if call.data == "p300": tag = "\n\n📍 <b>Статус: Популярный выбор</b>"
            if call.data == "p500": tag = "\n\n📍 <b>Статус: Самый выгодный вариант</b>"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💳 Купить за {item['price']}", url="https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад к выбору", callback_data="open_shop"))
            
            bot.edit_message_text(
                f"<b>Пакет: {item['name']} звёзд</b>\n"
                f"<i>{item['desc']}</i>"
                f"{tag}\n\n"
                f"<b>💰 Сумма к оплате: {item['price']}</b>",
                uid, call.message.id, parse_mode='HTML', reply_markup=markup
            )

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
