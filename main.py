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

# --- БД ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, spent INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

init_db()

def update_spent(uid, uname, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username, spent) VALUES (?, ?, 0)", (uid, uname))
    cursor.execute("UPDATE users SET spent = spent + ?, username = ? WHERE id = ?", (amount, uname, uid))
    conn.commit()
    conn.close()

# --- ДОП ---
user_orders = {}

# --- КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )
    markup.add(
        types.InlineKeyboardButton("🏆 Топ", callback_data="top"),
        types.InlineKeyboardButton("❓ Поддержка", url="https://t.me/yngsafar")
    )
    return markup

def shop_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="p1000"))
    markup.add(
        types.InlineKeyboardButton("⭐ 100 — 18 000 UZS", callback_data="p100"),
        types.InlineKeyboardButton("⭐ 150 — 27 000 UZS", callback_data="p150"),
        types.InlineKeyboardButton("⭐ 200 — 36 000 UZS", callback_data="p200"),
        types.InlineKeyboardButton("✅ ⭐ 250 — 40 000 UZS", callback_data="p250"),
        types.InlineKeyboardButton("🔥 ⭐ 300 — 48 000 UZS", callback_data="p300"),
        types.InlineKeyboardButton("⭐ 350 — 56 000 UZS", callback_data="p350"),
        types.InlineKeyboardButton("⭐ 400 — 64 000 UZS", callback_data="p400"),
        types.InlineKeyboardButton("⭐ 450 — 72 000 UZS", callback_data="p450")
    )
    markup.row(types.InlineKeyboardButton("💎 ⭐ 500 — 80 000 UZS", callback_data="p500"))
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
    return markup

PRICES = {
    "p100": 18000, "p150": 27000, "p200": 36000, "p250": 40000,
    "p300": 48000, "p350": 56000, "p400": 64000, "p450": 72000,
    "p500": 80000, "p1000": 145000
}

# --- СТАРТ ---
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
        bot.edit_message_text("🛒 <b>Выберите пакет:</b>", uid, mid, parse_mode='HTML', reply_markup=shop_kb())

    elif call.data == "profile":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT spent FROM users WHERE id=?", (uid,))
        res = cur.fetchone()
        conn.close()
        spent = res[0] if res else 0

        bot.edit_message_text(
            f"👤 <b>Профиль</b>\n🆔 <code>{uid}</code>\n💰 Потрачено: <b>{spent} UZS</b>",
            uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
        )

    elif call.data == "top":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users ORDER BY spent DESC LIMIT 10")
        res = cur.fetchall()
        conn.close()

        text = "<b>🏆 Топ:</b>\n\n"
        for i, r in enumerate(res, 1):
            text += f"{i}. {r[0]} — {r[1]} UZS\n"

        bot.edit_message_text(text, uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
        )

    elif call.data in PRICES:
        count = int(call.data.replace('p',''))
        pay_screen(uid, mid, count, PRICES[call.data])

    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c, p = parts[1], parts[2]

        user_orders[uid] = {"count": c, "price": p}

        msg = bot.edit_message_text(
            "👤 Введите username получателя (@username):",
            uid, mid
        )
        bot.register_next_step_handler(msg, get_username)

    elif call.data == "custom":
        msg = bot.edit_message_text("Введите количество (мин 100):", uid, mid)
        bot.register_next_step_handler(msg, custom_logic)

    # --- АДМИН ---
    elif call.data.startswith("adm_ok|"):
        parts = call.data.split("|")
        cid, amt, uname = parts[1], parts[2], parts[3]

        update_spent(int(cid), uname, int(amt))

        bot.send_message(cid,
            "✅ <b>Ваша заявка подтверждена!</b>\n\n"
            "Звезды будут начислены на ваш баланс в течении нескольких часов.\n\n"
            "Не пришли звезды? Обращайся в поддержку @RandomGamesUzbAdmin",
            parse_mode='HTML'
        )

        bot.edit_message_caption("✅ Оплачено", call.message.chat.id, call.message.id)

    elif call.data.startswith("adm_no|"):
        cid = call.data.split("|")[1]

        bot.send_message(cid,
            "❌ Заявка отклонена. Напишите в поддержку.",
            parse_mode='HTML'
        )

        bot.edit_message_caption("❌ Отклонено", call.message.chat.id, call.message.id)

# --- USERNAME ---
def get_username(message):
    uid = message.from_user.id
    username = message.text.strip()

    if not username.startswith("@"):
        msg = bot.send_message(uid, "❌ Введите @username")
        bot.register_next_step_handler(msg, get_username)
        return

    user_orders[uid]["target"] = username

    msg = bot.send_message(uid, "📸 Отправьте чек:")
    bot.register_next_step_handler(msg, finish_order_with_target)

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

    bot.send_message(uid,
        "✅ <b>Ваша заявка подтверждена!</b>\n\n"
        "Звезды будут начислены на ваш баланс в течении нескольких часов.\n\n"
        "Не пришли звезды? Обращайся в поддержку @RandomGamesUzbAdmin",
        parse_mode='HTML',
        reply_markup=main_kb(uid)
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok|{uid}|{p}|{uname}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no|{uid}"))

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"👤 @{uname}\n🎯 {target}\n⭐ {c}\n💰 {p} UZS",
        reply_markup=kb
    )

# --- CUSTOM ---
def custom_logic(message):
    try:
        count = int(message.text)

        if count < 100:
            msg = bot.send_message(message.chat.id, "❌ Минимум 100, попробуй снова:")
            bot.register_next_step_handler(msg, custom_logic)
            return

        price = count * 180
        pay_screen(message.chat.id, None, count, price)

    except:
        msg = bot.send_message(message.chat.id, "⚠️ Введите число:")
        bot.register_next_step_handler(msg, custom_logic)

# --- ОПЛАТА ---
def pay_screen(uid, mid, c, p):
    text = f"💳 К оплате: {p} UZS\n⭐ {c}\n\n{CARD_DETAILS}"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("❌ Отмена", callback_data="shop"))

    if mid:
        bot.edit_message_text(text, uid, mid, reply_markup=kb)
    else:
        bot.send_message(uid, text, reply_markup=kb)

# --- СТАРТ ---
if __name__ == "__main__":
    bot.infinity_polling()
