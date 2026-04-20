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

ADMIN_ID = 1411441331 
CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

# ЦЕНЫ
STARS_PACKS = {
    "p100": {"name": "⭐ 100", "price": 18000, "count": 100},
    "p150": {"name": "⭐ 150", "price": 27000, "count": 150},
    "p200": {"name": "⭐ 200", "price": 36000, "count": 200},
    "p250": {"name": "✅ 250", "price": 40000, "count": 250},
    "p300": {"name": "🔥 300", "price": 48000, "count": 300},
    "p350": {"name": "⭐ 350", "price": 56000, "count": 350},
    "p400": {"name": "⭐ 400", "price": 64000, "count": 400},
    "p450": {"name": "⭐ 450", "price": 72000, "count": 450},
    "p500": {"name": "💎 500", "price": 80000, "count": 500},
    "special": {"name": "🎁 ОСОБОЕ", "price": 145000, "count": 1000}
}

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
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        types.InlineKeyboardButton("🏆 Топ", callback_data="top"),
        types.InlineKeyboardButton("❓ Поддержка", url="https://t.me/yngsafar")
    )
    return markup

def shop_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ: 1000 ⭐ — 145 000 UZS", callback_data="special"))
    for k in ["p100", "p150", "p200", "p250", "p300", "p350", "p400", "p450", "p500"]:
        v = STARS_PACKS[k]
        markup.insert(types.InlineKeyboardButton(f"{v['name']} — {v['price']:,}".replace(',',' '), callback_data=k))
    markup.row(types.InlineKeyboardButton("✨ СВОЯ СУММА", callback_data="custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
    return markup

# --- ОБРАБОТКА ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    bot.send_message(message.chat.id, f"<b>Привет, {message.from_user.first_name}!</b>\nВыбирай звезды по лучшей цене:", 
                     parse_mode='HTML', reply_markup=main_kb(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        bot.edit_message_text("<b>Главное меню:</b>", uid, mid, parse_mode='HTML', reply_markup=main_kb(uid))
    elif call.data == "shop":
        bot.edit_message_text("<b>Выберите пакет звёзд:</b>", uid, mid, parse_mode='HTML', reply_markup=shop_kb())
    elif call.data == "profile":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT spent FROM users WHERE id=?", (uid,)); res = cur.fetchone(); conn.close()
        spent = res[0] if res else 0
        bot.edit_message_text(f"<b>👤 Профиль</b>\nID: <code>{uid}</code>\nПотрачено: <b>{spent:,} UZS</b>".replace(',',' '), 
                              uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))
    elif call.data == "top":
        conn = sqlite3.connect('users.db'); cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users WHERE spent > 0 ORDER BY spent DESC LIMIT 10"); res = cur.fetchall(); conn.close()
        text = "<b>🏆 Топ донатеров:</b>\n\n"
        for i, r in enumerate(res, 1): text += f"{i}. {r[0]} — {r[1]:,} UZS\n".replace(',',' ')
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))
    elif call.data == "custom":
        msg = bot.edit_message_text("<b>⌨️ Введи количество звёзд:</b>", uid, mid, parse_mode='HTML')
        bot.register_next_step_handler(msg, custom_logic)
    elif call.data in STARS_PACKS:
        pay_screen(uid, mid, STARS_PACKS[call.data]['count'], STARS_PACKS[call.data]['price'])
    elif call.data.startswith("pay_"):
        _, c, p = call.data.split("_")
        msg = bot.edit_message_text("<b>🧾 Отправь фото чека:</b>", uid, mid, parse_mode='HTML')
        bot.register_next_step_handler(msg, finish_order, c, p)
    
    # ЛОГИКА АДМИН-ПАНЕЛИ
    elif call.data.startswith("adm_ok_"):
        _, cid, amt, uname = call.data.split("_")
        update_spent(int(cid), uname, int(amt))
        bot.answer_callback_query(call.id, "✅ Зачислено!")
        confirm_text = (
            "✅ <b>Ваша заявка подтверждена!</b>\n\n"
            "Звезды будут начислены на ваш баланс в течении нескольких часов. "
            "Не пришли звезды? Обращайся в поддержку @RandomGamesUzbAdmin"
        )
        bot.send_message(cid, confirm_text, parse_mode='HTML')
        bot.edit_message_caption(caption="✅ <b>Оплачено</b>", chat_id=call.message.chat.id, message_id=mid, parse_mode='HTML')
    
    # ИСПРАВЛЕННАЯ КНОПКА ОТМЕНЫ
    elif call.data.startswith("adm_no_"):
        _, cid = call.data.split("_")
        bot.answer_callback_query(call.id, "❌ Отклонено")
        bot.send_message(cid, "❌ <b>Ваша заявка отклонена.</b>\nЧек не прошел проверку. Если это ошибка, напишите в поддержку.")
        bot.edit_message_caption(caption="❌ <b>Отклонено</b>", chat_id=call.message.chat.id, message_id=mid, parse_mode='HTML')

def custom_logic(message):
    try:
        count = int(message.text)
        price = count * (160 if count >= 250 else 180)
        pay_screen(message.chat.id, None, count, price)
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка! Введи только число.", reply_markup=shop_kb())

def pay_screen(uid, mid, c, p):
    text = f"<b>💳 К оплате: {int(p):,} UZS</b>\nТовар: {c} ⭐\n\n<code>{CARD_DETAILS}</code>".replace(',',' ')
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
    if mid: bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=kb)
    else: bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def finish_order(message, c, p):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Нужно фото чека!")
        bot.register_next_step_handler(msg, finish_order, c, p)
        return
    
    uid, uname = message.from_user.id, (message.from_user.username or message.from_user.first_name)
    bot.send_message(uid, "✅ <b>Чек отправлен!</b> Ожидай подтверждения админом.", reply_markup=main_kb(uid))
    
    # КНОПКИ ДЛЯ АДМИНА
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok_{uid}_{p}_{uname}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no_{uid}"))
    
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"💰 Чек: {int(p):,} UZS\n👤 От: @{uname}".replace(',',' '), reply_markup=kb)

if __name__ == "__main__":
    bot.infinity_polling()
