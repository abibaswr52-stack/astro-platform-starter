import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. НАСТРОЙКА ДЛЯ RENDER (АНТИ-СОН) ---
app = Flask('')
@app.route('/')
def home(): return "Бот-магазин активен 24/7!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ БОТА ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# НАСТРОЙКИ
ADMIN_ID = 123456789  # <--- ВСТАВЬ СВОЙ ID СЮДА
ADMIN_USERNAME = "@yngsafar"

# ДАННЫЕ МАГАЗИНА
STARS_PACKS = {
    "special": {"name": "🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ", "price": "145,000 UZS", "desc": "💎 1000 звёзд по супер-цене! (Ограничено)"},
    "p100": {"name": "⭐ 100", "price": "18,000 UZS", "desc": "Базовый пакет"},
    "p150": {"name": "⭐ 150", "price": "27,000 UZS", "desc": "Стандартный набор"},
    "p200": {"name": "⭐ 200", "price": "36,000 UZS", "desc": "Больше звезд — больше возможностей"},
    "p250": {"name": "⭐ 250", "price": "40,000 UZS", "desc": "✅ Оптимальный вариант (Скидка!)"},
    "p300": {"name": "⭐ 300", "price": "48,000 UZS", "desc": "🔥 Популярный выбор"},
    "p350": {"name": "⭐ 350", "price": "56,000 UZS", "desc": "Цена за 100 шт снижена"},
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
    # Кнопка особого предложения сверху на всю ширину
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="special"))
    
    btns = []
    for k, v in STARS_PACKS.items():
        if k == "special": continue
        prefix = ""
        if k == "p250": prefix = "✅ "
        if k == "p300": prefix = "🔥 "
        if k == "p500": prefix = "💎 "
        btns.append(types.InlineKeyboardButton(f"{prefix}{v['name']} — {v['price']}", callback_data=k))
    
    markup.add(*btns)
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="ask_custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="main_menu"))
    return markup

# --- 4. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"<b>Привет, {message.from_user.first_name}!</b>\nДобро пожаловать в магазин звёзд.",
        parse_mode='HTML', reply_markup=main_menu_markup(message.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    try:
        if call.data == "main_menu":
            bot.edit_message_text("<b>Главное меню:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=main_menu_markup(uid))

        elif call.data == "open_shop":
            bot.edit_message_text("<b>Выберите количество звёзд:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=shop_menu_markup())

        elif call.data == "ask_custom":
            msg = bot.edit_message_text("<b>Введите количество звёзд (число):</b>\nНапример: 693", uid, call.message.id, parse_mode='HTML')
            bot.register_next_step_handler(msg, process_custom_amount)

        elif call.data == "profile":
            text = f"<b>👤 Профиль</b>\n\n<b>Имя:</b> {call.from_user.first_name}\n<b>ID:</b> <code>{uid}</code>\n<b>Баланс:</b> 0 ⭐"
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', 
                                  reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))

        elif call.data == "help":
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👨‍💻 Админ @yngsafar", url=f"https://t.me/yngsafar"),
                                                     types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text("<b>❓ Поддержка</b>\nПо всем вопросам пишите админу:", uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data in STARS_PACKS:
            item = STARS_PACKS[call.data]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💳 Купить за {item['price']}", url=f"https://t.me/yngsafar"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="open_shop"))
            bot.edit_message_text(f"<b>Пакет: {item['name']}</b>\n<i>{item['desc']}</i>\n\n<b>💰 К оплате: {item['price']}</b>", 
                                  uid, call.message.id, parse_mode='HTML', reply_markup=markup)

    except Exception as e: print(f"Ошибка: {e}")

# --- ФУНКЦИЯ КАЛЬКУЛЯТОРА ЦЕНЫ ---
def process_custom_amount(message):
    uid = message.from_user.id
    try:
        amount = int(message.text)
        if amount < 100:
            bot.send_message(uid, "❌ Минимальный заказ — 100 звёзд.", reply_markup=shop_menu_markup())
            return

        # Ценовая политика: до 250 - 180 сум/шт, от 250 - 160 сум/шт
        price_per_one = 160 if amount >= 250 else 180
        total = amount * price_per_one
        
        text = (f"<b>📊 Расчет заказа:</b>\n\nКоличество: <b>{amount} ⭐</b>\n"
                f"Курс: {price_per_one} UZS/шт\n\n"
                f"💰 <b>Итого: {total:,} UZS</b>".replace(',', ' '))
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"💳 Оплатить {total:,} UZS".replace(',', ' '), url=f"https://t.me/yngsafar"))
        markup.add(types.InlineKeyboardButton("⬅️ В магазин", callback_data="open_shop"))
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=markup)
    except:
        bot.send_message(uid, "⚠️ Введите целое число.", reply_markup=shop_menu_markup())

if __name__ == "__main__":
    bot.infinity_polling()
