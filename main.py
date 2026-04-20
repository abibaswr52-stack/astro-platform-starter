import os
import telebot
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Shop is Online"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- КОНФИГ ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

ADMIN_ID = 1001209009 
CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

# Твои обновленные цены
STARS_PACKS = {
    "special": {"name": "🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ", "price": 145000, "count": 1000},
    "p100": {"name": "⭐ 100", "price": 18000, "count": 100},
    "p150": {"name": "⭐ 150", "price": 27000, "count": 150},
    "p200": {"name": "⭐ 200", "price": 36000, "count": 200},
    "p250": {"name": "✅ 250", "price": 40000, "count": 250},
    "p300": {"name": "🔥 300", "price": 48000, "count": 300},
    "p350": {"name": "⭐ 350", "price": 56000, "count": 350},
    "p400": {"name": "⭐ 400", "price": 64000, "count": 400},
    "p450": {"name": "⭐ 450", "price": 72000, "count": 450},
    "p500": {"name": "💎 500", "price": 80000, "count": 500}
}

# --- БД ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, username TEXT, spent INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def update_user_spent(uid, username, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username, spent) VALUES (?, ?, ?)", (uid, username, 0))
    cursor.execute("UPDATE users SET spent = spent + ?, username = ? WHERE id = ?", (amount, username, uid))
    conn.commit()
    conn.close()

def get_user_data(uid):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT spent FROM users WHERE id = ?", (uid,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def get_top_donators():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, spent FROM users WHERE spent > 0 ORDER BY spent DESC LIMIT 10")
    res = cursor.fetchall()
    conn.close()
    return res

# --- КЛАВИАТУРЫ ---
def main_menu_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        types.InlineKeyboardButton("🏆 Зал славы", callback_data="top_donators"),
        types.InlineKeyboardButton("❓ Поддержка", url="https://t.me/yngsafar")
    )
    if uid == ADMIN_ID:
        markup.row(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def shop_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🔥 1000 ⭐ ЗА 145 000 UZS", callback_data="special"))
    btns = []
    for k, v in STARS_PACKS.items():
        if k == "special": continue
        btns.append(types.InlineKeyboardButton(f"{v['name']} — {v['price']:,} UZS".replace(',', ' '), callback_data=k))
    markup.add(*btns)
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="ask_custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return markup

# --- ХЕНДЛЕРЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name
    update_user_spent(uid, uname, 0)
    welcome = (f"<b>👋 Приветствуем, {message.from_user.first_name}!</b>\n\n"
               f"Ты попал в <b>Premium Stars Shop</b>.\n"
               f"────────────────────────\n"
               f"⚡️ <b>Быстро.</b> 💎 <b>Выгодно.</b> 🛡 <b>Надежно.</b>")
    bot.send_message(message.chat.id, welcome, parse_mode='HTML', reply_markup=main_menu_markup(uid))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    mid = call.message.id

    if call.data == "main_menu":
        bot.edit_message_text("<b>🏠 Главное меню:</b>", uid, mid, parse_mode='HTML', reply_markup=main_menu_markup(uid))
    elif call.data == "open_shop":
        bot.edit_message_text("<b>🛍 Витрина товаров:</b>", uid, mid, parse_mode='HTML', reply_markup=shop_menu_markup())
    elif call.data == "profile":
        spent = get_user_data(uid)
        text = (f"<b>👤 Твой профиль</b>\n──────────────────\n🆔 ID: <code>{uid}</code>\n"
                f"💰 Потрачено: <b>{spent:,} UZS</b>\n──────────────────").replace(',', ' ')
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))
    elif call.data == "top_donators":
        top = get_top_donators()
        text = "<b>🏆 Топ донатеров</b>\n\n"
        for i, (name, amount) in enumerate(top, 1):
            text += f"{i}. <code>{name}</code> — <b>{amount:,} UZS</b>\n".replace(',', ' ')
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))
    elif call.data == "ask_custom":
        msg = bot.edit_message_text("<b>⌨️ Введите количество звёзд:</b>", uid, mid, parse_mode='HTML')
        bot.clear_step_handler_by_chat_id(uid)
        bot.register_next_step_handler(msg, process_custom_amount)
    elif call.data in STARS_PACKS:
        show_payment(uid, mid, STARS_PACKS[call.data]['count'], STARS_PACKS[call.data]['price'])
    elif call.data.startswith("paid_"):
        _, count, price = call.data.split("_")
        ask_receipt(uid, mid, count, price)
    
    # Кнопки для Админа (Подтверждение)
    elif call.data.startswith("confirm_"):
        _, client_id, amount, username = call.data.split("_")
        update_user_spent(int(client_id), username, int(amount))
        bot.answer_callback_query(call.id, "✅ Зачислено!")
        bot.send_message(client_id, "✅ <b>Ваша оплата подтверждена!</b>\nЗвезды начислены.")
        bot.edit_message_caption("✅ <b>Оплачено</b>", call.message.chat.id, mid)

def show_payment(uid, mid, count, price):
    text = (f"<b>💳 Оплата: {count} ⭐</b>\n──────────────────\n💰 Сумма: <b>{int(price):,} UZS</b>\n"
            f"🏦 Карта: <code>{CARD_DETAILS}</code>\n──────────────────").replace(',', ' ')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{count}_{price}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="open_shop"))
    bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=markup)

def ask_receipt(uid, mid, count, price):
    bot.edit_message_text("<b>🧾 Отправьте фото чека:</b>", uid, mid, parse_mode='HTML')
    bot.clear_step_handler_by_chat_id(uid)
    bot.register_next_step_handler_by_chat_id(uid, process_finish, count, price)

def process_finish(message, count, price):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "⚠️ Отправьте фото чека!")
        bot.register_next_step_handler(msg, process_finish, count, price)
        return
    
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name
    bot.send_message(uid, "✅ <b>Заявка принята, ожидайте ответ админа!</b>", reply_markup=main_menu_markup(uid))
    
    # Админу прилетает чек с кнопкой подтверждения
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{uid}_{price}_{uname}"))
    markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data="main_menu"))
    
    admin_cap = f"🔔 <b>ЗАКАЗ!</b>\nКлиент: @{uname}\nID: {uid}\nТовар: {count} ⭐\nСумма: {int(price):,} UZS".replace(',', ' ')
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_cap, parse_mode='HTML', reply_markup=markup)

def process_custom_amount(message):
    try:
        count = int(message.text)
        price = count * (160 if count >= 250 else 180)
        show_payment(message.chat.id, None, count, price)
    except:
        bot.send_message(message.chat.id, "⚠️ Введите число!")

if __name__ == "__main__":
    bot.infinity_polling()
