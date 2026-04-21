import os
import telebot
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread
import time

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

# --- ДОП ДАННЫЕ ---
last_orders = {}
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

# --- ОБРАБОТКА ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    welcome_text = (
        f"🌟 Добро пожаловать в <b>RandomStarsUzb</b>, <b>{message.from_user.first_name}</b>!\n\n"
        "💎 Мгновенная покупка Telegram Stars\n"
        "⚡ Быстрое зачисление\n"
        "🔒 Гарантия безопасности\n\n"
        "👇 Выберите действие:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_kb(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        welcome_text = f"🌟 Добро пожаловать, <b>{call.from_user.first_name}</b>!\n\nВыберите раздел:"
        bot.edit_message_text(welcome_text, uid, mid, parse_mode='HTML', reply_markup=main_kb(uid))

    elif call.data == "shop":
        bot.edit_message_text(
            "🛒 <b>Выберите пакет звёзд:</b>\n\n💡 Чем больше — тем выгоднее цена за 1 ⭐",
            uid, mid, parse_mode='HTML', reply_markup=shop_kb()
        )

    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c, p = parts[1], parts[2]

        user_orders[uid] = {"count": c, "price": p}

        msg = bot.edit_message_text(
            "<b>👤 Введите username получателя:</b>\n\nПример: @username",
            uid, mid, parse_mode='HTML'
        )
        bot.register_next_step_handler(msg, get_username)

    elif call.data == "custom":
        msg = bot.edit_message_text("<b>Введите количество звёзд (минимум 100):</b>", uid, mid, parse_mode='HTML')
        bot.register_next_step_handler(msg, custom_logic)

# --- ВВОД USERNAME ---
def get_username(message):
    uid = message.from_user.id
    username = message.text.strip()

    if not username.startswith("@"):
        msg = bot.send_message(uid, "❌ Введите корректный username (начинается с @)")
        bot.register_next_step_handler(msg, get_username)
        return

    user_orders[uid]["target"] = username

    msg = bot.send_message(uid, "<b>🧾 Отправьте фото чека:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, finish_order_with_target)

# --- ФИНАЛ С ЗАКАЗОМ ---
def finish_order_with_target(message):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Отправьте фото чека!")
        bot.register_next_step_handler(msg, finish_order_with_target)
        return

    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name

    # антиспам
    now = time.time()
    if uid in last_orders and now - last_orders[uid] < 30:
        bot.send_message(uid, "⏳ Подожди немного перед новой заявкой.")
        return
    last_orders[uid] = now

    order = user_orders.get(uid, {})
    c = order.get("count")
    p = order.get("price")
    target = order.get("target", "не указан")

    bot.send_message(uid,
        "✅ <b>Чек получен!</b>\n\n⏳ Проверяем оплату (5–15 минут)",
        parse_mode='HTML',
        reply_markup=main_kb(uid)
    )

    admin_caption = (
        f"📩 <b>Новый заказ!</b>\n\n"
        f"👤 <b>От:</b> @{uname}\n"
        f"🎯 <b>Кому:</b> {target}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"💰 <b>Сумма:</b> <code>{int(p):,} UZS</code>\n"
        f"⭐ <b>Количество:</b> <code>{c} шт.</code>"
    ).replace(',', ' ')

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok_{uid}_{p}_{uname}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no_{uid}"))

    bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                   caption=admin_caption,
                   parse_mode='HTML',
                   reply_markup=kb)

# --- CUSTOM ---
def custom_logic(message):
    try:
        count = int(message.text)

        if count < 100:
            bot.send_message(message.chat.id, "❌ Минимальный заказ — 100 ⭐")
            return

        if count >= 500:
            price = count * 145
        elif count >= 250:
            price = count * 160
        else:
            price = count * 180

        pay_screen(message.chat.id, None, count, price)
    except:
        bot.send_message(message.chat.id, "⚠️ Введите число.", reply_markup=shop_kb())

# --- PAY ---
def pay_screen(uid, mid, c, p):
    text = f"<b>💳 К оплате: {int(p):,} UZS</b>\n⭐ {c} шт.\n\n<code>{CARD_DETAILS}</code>".replace(',',' ')
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    if mid:
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

# --- СТАРТ ---
if __name__ == "__main__":
    bot.infinity_polling()

