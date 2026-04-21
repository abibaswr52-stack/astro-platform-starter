import os
import telebot
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home(): return "Shop Status: OK"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- КОНФИГ ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

ADMIN_ID = 1001209009
CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

ADMIN_BALANCE = 0
user_orders = {}

# --- БД ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            spent INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT NULL,
            ref_earned INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# --- UPDATE SPENT ---
def update_spent(uid, uname, amount):
    global ADMIN_BALANCE

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO users (id, username, spent) VALUES (?, ?, 0)", (uid, uname))
    cur.execute("UPDATE users SET spent = spent + ?, username = ? WHERE id = ?", (amount, uname, uid))

    # рефералка
    cur.execute("SELECT referrer_id FROM users WHERE id=?", (uid,))
    ref = cur.fetchone()

    if ref and ref[0]:
        bonus = int(amount * 0.02)
        cur.execute("UPDATE users SET ref_earned = ref_earned + ? WHERE id=?", (bonus, ref[0]))

    ADMIN_BALANCE += amount

    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )

    markup.add(
        types.InlineKeyboardButton("🏆 Топ", callback_data="top"),
        types.InlineKeyboardButton("👥 Рефералка", callback_data="ref")
    )

    markup.add(
        types.InlineKeyboardButton("💰 Баланс админа", callback_data="admin_balance"),
        types.InlineKeyboardButton("🗑 Удалить заказ", callback_data="delete")
    )

    markup.add(
        types.InlineKeyboardButton("❓ Поддержка", url="https://t.me/yngsafar")
    )

    return markup

# --- SHOP ---
def shop_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="p1000"))
    markup.add(
        types.InlineKeyboardButton("⭐ 100 — 18 000 UZS", callback_data="p100"),
        types.InlineKeyboardButton("⭐ 150 — 27 000 UZS", callback_data="p150"),
        types.InlineKeyboardButton("⭐ 200 — 36 000 UZS", callback_data="p200"),
        types.InlineKeyboardButton("⭐ 250 — 40 000 UZS", callback_data="p250"),
        types.InlineKeyboardButton("⭐ 300 — 48 000 UZS", callback_data="p300"),
        types.InlineKeyboardButton("⭐ 350 — 56 000 UZS", callback_data="p350"),
        types.InlineKeyboardButton("⭐ 400 — 64 000 UZS", callback_data="p400"),
        types.InlineKeyboardButton("⭐ 450 — 72 000 UZS", callback_data="p450")
    )
    markup.row(types.InlineKeyboardButton("⭐ 500 — 80 000 UZS", callback_data="p500"))
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
    return markup

PRICES = {
    "p100": 18000, "p150": 27000, "p200": 36000, "p250": 40000,
    "p300": 48000, "p350": 56000, "p400": 64000, "p450": 72000,
    "p500": 80000, "p1000": 145000
}

# --- START ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    text = (
        f"🌟 Добро пожаловать в <b>RandomStarsUzb</b>, <b>{message.from_user.first_name}</b>!\n\n"
        "💎 Быстрая покупка Telegram Stars\n"
        "⚡ Безопасно и надежно\n\n"
        "👇 Выберите действие:"
    )

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_kb(message.from_user.id))

# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        bot.edit_message_text("🏠 Главное меню:", uid, mid, reply_markup=main_kb(uid))

    elif call.data == "shop":
        bot.edit_message_text("🛒 Выберите пакет:", uid, mid, reply_markup=shop_kb())

    elif call.data == "profile":
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT spent FROM users WHERE id=?", (uid,))
        res = cur.fetchone()
        conn.close()

        spent = res[0] if res else 0

        bot.edit_message_text(f"👤 Профиль\n💰 {spent}", uid, mid)

    elif call.data == "top":
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users ORDER BY spent DESC LIMIT 10")
        res = cur.fetchall()
        conn.close()

        text = "🏆 TOP\n\n"
        for i, r in enumerate(res, 1):
            text += f"{i}. {r[0]} - {r[1]}\n"

        bot.edit_message_text(text, uid, mid)

    elif call.data == "ref":
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (uid,))
        invited = cur.fetchone()[0]

        cur.execute("SELECT ref_earned FROM users WHERE id=?", (uid,))
        earned = cur.fetchone()
        earned = earned[0] if earned else 0

        conn.close()

        bot.edit_message_text(f"👥 {invited}\n💰 {earned}", uid, mid)

    elif call.data == "admin_balance":
        bot.answer_callback_query(call.id, f"Баланс админа: {ADMIN_BALANCE}")

    elif call.data == "delete":
        user_orders.pop(uid, None)
        bot.answer_callback_query(call.id, "Удалено")

    elif call.data in PRICES:
        c = int(call.data.replace("p",""))
        pay_screen(uid, mid, c, PRICES[call.data])

# --- PAY ---
def pay_screen(uid, mid, c, p):
    text = f"💳 {p} UZS\n⭐ {c}\n\n{CARD_DETAILS}"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Я оплатил", callback_data=f"pay_{c}_{p}"))

    if mid:
        bot.edit_message_text(text, uid, mid, reply_markup=kb)
    else:
        bot.send_message(uid, text, reply_markup=kb)

# --- ФИНАЛ ---
def finish_order_with_target(message):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Нужен фото чек")
        bot.register_next_step_handler(msg, finish_order_with_target)
        return

    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name

    order = user_orders.get(uid, {})
    c = order.get("count")
    p = order.get("price")
    target = order.get("target", "не указан")

    bot.send_message(
        uid,
        "✅ <b>Ваша заявка подтверждена!</b>\n\n"
        "Звезды будут начислены на ваш баланс в течении нескольких часов.\n\n"
        "Не пришли звезды? Обращайся в поддержку @RandomGamesUzbAdmin",
        parse_mode='HTML',
        reply_markup=main_kb(uid)
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"adm_ok|{uid}|{p}|{uname}"))
    kb.add(types.InlineKeyboardButton("Отклонить", callback_data=f"adm_no|{uid}"))

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"{uname}\n{target}\n{c}\n{p}",
        reply_markup=kb
    )

# --- CUSTOM ---
def custom_logic(message):
    try:
        count = int(message.text)
        if count < 100:
            msg = bot.send_message(message.chat.id, "Минимум 100")
            bot.register_next_step_handler(msg, custom_logic)
            return

        price = count * 180
        pay_screen(message.chat.id, None, count, price)

    except:
        msg = bot.send_message(message.chat.id, "Введите число")
        bot.register_next_step_handler(msg, custom_logic)

# --- START BOT ---
if __name__ == "__main__":
    bot.infinity_polling()
