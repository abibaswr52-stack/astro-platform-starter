import os
import telebot
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ ---
app = Flask('')
@app.route('/')
def home(): return "Premium Stars Shop is Active"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ И БД ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

ADMIN_ID = 1001209009
CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

def init_db():
    conn = sqlite3.connect('users.db')
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

# --- 3. ЦЕНЫ И ДИЗАЙН ---
STARS_PACKS = {
    "special": {"name": "🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ", "price": 145000, "count": 1000},
    "p100": {"name": "⭐ 100", "price": 18000, "count": 100},
    "p250": {"name": "✅ 250", "price": 40000, "count": 250},
    "p500": {"name": "💎 500", "price": 80000, "count": 500}
}

# --- 4. КЛАВИАТУРЫ ---

def main_menu_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        types.InlineKeyboardButton("🏆 Зал славы", callback_data="top_donators"),
        types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    )
    return markup

def shop_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🔥 ОСОБОЕ: 1000 ⭐ — 145 000 UZS", callback_data="special"))
    
    # Основные паки
    btns = [
        types.InlineKeyboardButton("⭐ 100 — 18к", callback_data="p100"),
        types.InlineKeyboardButton("✅ 250 — 40к", callback_data="p250"),
        types.InlineKeyboardButton("💎 500 — 80к", callback_data="p500")
    ]
    markup.add(*btns)
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="ask_custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return markup

# --- 5. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name
    update_user_spent(uid, uname, 0) # Просто регаем в базе
    
    text = (f"<b>👋 Привет, {message.from_user.first_name}!</b>\n\n"
            f"Добро пожаловать в <b>Premium Stars Shop</b>.\n"
            f"Здесь ты можешь быстро и безопасно купить Telegram Stars.")
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu_markup(uid))

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
        text = (f"<b>👤 Твой профиль</b>\n"
                f"──────────────────\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"💰 Потрачено всего: <b>{spent:,} UZS</b>\n"
                f"🌟 Ранг: {'💎 Кит' if spent > 500000 else '⭐ Покупатель'}\n"
                f"──────────────────").replace(',', ' ')
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', 
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))

    elif call.data == "top_donators":
        top = get_top_donators()
        text = "<b>🏆 Топ донатеров (Зал славы)</b>\n\n"
        if not top:
            text += "<i>Пока здесь пусто... Будь первым!</i>"
        else:
            for i, (name, amount) in enumerate(top, 1):
                icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
                text += f"{icon} {name} — <b>{amount:,} UZS</b>\n".replace(',', ' ')
        
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', 
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))

    elif call.data == "ask_custom":
        msg = bot.edit_message_text("<b>⌨️ Введите количество звёзд (число):</b>\nНапример: 693", uid, mid, parse_mode='HTML',
                                    reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Отмена", callback_data="open_shop")))
        bot.register_next_step_handler(msg, process_custom_amount)

    elif call.data in STARS_PACKS:
        item = STARS_PACKS[call.data]
        show_payment(uid, mid, item['count'], item['price'])

    elif call.data.startswith("paid_"):
        _, count, price = call.data.split("_")
        ask_receipt(uid, mid, count, price)

# --- ЛОГИКА ОПЛАТЫ ---

def show_payment(uid, mid, count, price):
    text = (f"<b>💳 Оплата: {count} ⭐</b>\n"
            f"──────────────────\n"
            f"💵 Сумма: <b>{int(price):,} UZS</b>\n"
            f"🏦 Карта: <code>{CARD_DETAILS}</code>\n"
            f"──────────────────\n"
            f"Нажми кнопку после перевода:").replace(',', ' ')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{count}_{price}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="open_shop"))
    
    if mid:
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=markup)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=markup)

def ask_receipt(uid, mid, count, price):
    bot.edit_message_text("<b>🧾 Отправьте фото чека для подтверждения:</b>", uid, mid, parse_mode='HTML')
    bot.register_next_step_handler_by_chat_id(uid, process_finish, count, price)

def process_finish(message, count, price):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "⚠️ Нужно прислать именно <b>фото</b> чека!")
        bot.register_next_step_handler(msg, process_finish, count, price)
        return

    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name
    
    # Обновляем статистику трат (после проверки админом в реальности, но тут для теста сразу)
    update_user_spent(uid, uname, int(price))
    
    bot.send_message(uid, "✅ <b>Заявка принята!</b>\nАдмин проверит чек и начислит звезды.", 
                     parse_mode='HTML', reply_markup=main_menu_markup(uid))
    
    bot.send_message(ADMIN_ID, f"🚀 <b>Заказ!</b>\nОт: @{uname}\nТовар: {count} ⭐\nЦена: {int(price):,} UZS".replace(',', ' '))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id)

def process_custom_amount(message):
    try:
        count = int(message.text)
        if count < 100:
            bot.send_message(message.chat.id, "❌ Минимум 100 ⭐", reply_markup=shop_menu_markup())
            return
        price = count * (160 if count >= 250 else 180)
        show_payment(message.chat.id, None, count, price)
    except:
        bot.send_message(message.chat.id, "⚠️ Введите число!", reply_markup=shop_menu_markup())

if __name__ == "__main__":
    bot.infinity_polling()
