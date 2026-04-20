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
        "Мы предоставляем самые выгодные цены на Telegram Stars в Узбекистане. 🇺🇿\n"
        "Быстро, надежно и с гарантией.\n\n"
        "Выбирай нужный раздел ниже и приступай к покупкам! 👇"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_kb(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        welcome_text = (
            f"🌟 Добро пожаловать в <b>RandomStarsUzb</b>, <b>{call.from_user.first_name}</b>!\n\n"
            "Выберите раздел:"
        )
        bot.edit_message_text(welcome_text, uid, mid, parse_mode='HTML', reply_markup=main_kb(uid))
    elif call.data == "shop":
        bot.edit_message_text("<b>Выберите количество звёзд:</b>", uid, mid, parse_mode='HTML', reply_markup=shop_kb())
    elif call.data == "profile":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT spent FROM users WHERE id=?", (uid,)); res = cur.fetchone(); conn.close()
        spent = res[0] if res else 0
        bot.edit_message_text(f"<b>👤 Мой профиль</b>\n🆔 ID: <code>{uid}</code>\n💰 Потрачено: <b>{spent:,} UZS</b>".replace(',',' '), 
                              uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))
    elif call.data == "top":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users WHERE spent > 0 ORDER BY spent DESC LIMIT 10"); res = cur.fetchall(); conn.close()
        text = "<b>🏆 Топ донатеров:</b>\n\n"
        for i, r in enumerate(res, 1): text += f"{i}. {r[0]} — {r[1]:,} UZS\n".replace(',',' ')
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))
    elif call.data == "custom":
        msg = bot.edit_message_text("<b>Введите количество звёзд (число):</b>", uid, mid, parse_mode='HTML', 
                                    reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Отмена", callback_data="shop")))
        bot.register_next_step_handler(msg, custom_logic)
    elif call.data in PRICES:
        count = int(call.data.replace('p',''))
        pay_screen(uid, mid, count, PRICES[call.data])
    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c, p = parts[1], parts[2]
        msg = bot.edit_message_text("<b>🧾 Отправьте фото чека:</b>", uid, mid, parse_mode='HTML')
        bot.register_next_step_handler(msg, finish_order, c, p)
    
    # ЛОГИКА АДМИНА
    elif call.data.startswith("adm_ok_"):
        parts = call.data.split("_")
        cid, amt, uname = parts[2], parts[3], parts[4]
        update_spent(int(cid), uname, int(amt))
        confirm_text = (
            "✅ <b>Ваша заявка подтверждена!</b>\n\n"
            "Звезды будут начислены на ваш баланс в течении нескольких часов. "
            "Не пришли звезды? Обращайся в поддержку @RandomGamesUzbAdmin"
        )
        bot.send_message(cid, confirm_text, parse_mode='HTML')
        bot.edit_message_caption(caption="✅ <b>Оплачено</b>", chat_id=call.message.chat.id, message_id=mid, parse_mode='HTML')
    elif call.data.startswith("adm_no_"):
        parts = call.data.split("_")
        cid = parts[2] # Исправлено: берем 2-й индекс для ID пользователя
        bot.send_message(cid, "❌ <b>Заявка отклонена.</b>\nЕсли это ошибка, напишите в поддержку.", parse_mode='HTML')
        bot.edit_message_caption(caption="❌ <b>Отклонено</b>", chat_id=call.message.chat.id, message_id=mid, parse_mode='HTML')

def custom_logic(message):
    try:
        count = int(message.text)
        price = count * (160 if count >= 250 else 180)
        pay_screen(message.chat.id, None, count, price)
    except:
        bot.send_message(message.chat.id, "⚠️ Введите число.", reply_markup=shop_kb())

def pay_screen(uid, mid, c, p):
    text = f"<b>💳 К оплате: {int(p):,} UZS</b>\nТовар: {c} ⭐\n\nРеквизиты:\n<code>{CARD_DETAILS}</code>".replace(',',' ')
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
    if mid: bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=kb)
    else: bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def finish_order(message, c, p):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Отправьте фото чека!")
        bot.register_next_step_handler(msg, finish_order, c, p)
        return
    uid, uname = message.from_user.id, (message.from_user.username or message.from_user.first_name)
    bot.send_message(uid, "✅ <b>Чек отправлен!</b> Ожидайте подтверждения.", parse_mode='HTML', reply_markup=main_kb(uid))
    
    admin_caption = (
        f"📩 <b>Новый заказ!</b>\n\n"
        f"👤 <b>Пользователь:</b> @{uname}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"💰 <b>Сумма:</b> <code>{int(p):,} UZS</code>\n"
        f"⭐ <b>Количество:</b> <code>{c} шт.</code>"
    ).replace(',',' ')
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok_{uid}_{p}_{uname}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no_{uid}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_caption, parse_mode='HTML', reply_markup=kb)

if __name__ == "__main__":
    bot.infinity_polling()
