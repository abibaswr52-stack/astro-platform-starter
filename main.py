import os
import telebot
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread

# --- СЕРВЕР ---
app = Flask('')
@app.route('/')
def home():
    return "Shop Status: OK"

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
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            spent INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT NULL,
            ref_earned INTEGER DEFAULT 0,
            ref_balance INTEGER DEFAULT 0
        )
    ''')

    # Добавляем ref_balance если его нет (для старых баз)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN ref_balance INTEGER DEFAULT 0")
    except:
        pass

    # Таблица заявок на вывод реф. бонусов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ref_withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending'
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# --- UPDATE ---
def update_spent(uid, uname, amount):
    global ADMIN_BALANCE

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO users (id, username, spent) VALUES (?, ?, 0)", (uid, uname))
    cur.execute("UPDATE users SET spent = spent + ?, username = ? WHERE id = ?", (amount, uname, uid))

    cur.execute("SELECT referrer_id FROM users WHERE id=?", (uid,))
    ref = cur.fetchone()

    if ref and ref[0]:
        bonus = int(amount * 0.02)
        # ++ ref_earned (накопленный итог) и ref_balance (доступно для вывода)
        cur.execute("UPDATE users SET ref_earned = ref_earned + ?, ref_balance = ref_balance + ? WHERE id=?",
                    (bonus, bonus, ref[0]))

    ADMIN_BALANCE += amount

    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ (НЕ ТРОГАЮ ТВОЮ ЛОГИКУ) ---
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

# --- START (НЕ МЕНЯЛ ТВОЙ ТЕКСТ) ---
@bot.message_handler(commands=['start'])
def welcome(message):

    # 🔥 РЕФ КОД (ВОТ ЭТО БЫЛО СЛОМАНО РАНЬШЕ)
    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1].replace("ref_", ""))

            conn = sqlite3.connect('users.db')
            cur = conn.cursor()

            cur.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
                        (message.from_user.id, message.from_user.username or ""))

            cur.execute("SELECT referrer_id FROM users WHERE id=?", (message.from_user.id,))
            res = cur.fetchone()

            if res and res[0] is None:
                cur.execute("UPDATE users SET referrer_id=? WHERE id=?",
                            (ref_id, message.from_user.id))

            conn.commit()
            conn.close()
        except:
            pass

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
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT spent FROM users WHERE id=?", (uid,))
        res = cur.fetchone()
        conn.close()

        spent = res[0] if res else 0

        # ← Кнопка "Назад" уже была, оставляем
        bot.edit_message_text(
            f"👤 <b>Профиль</b>\n💰 Потрачено: {spent} UZS",
            uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
            )
        )

    elif call.data == "top":
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users ORDER BY spent DESC LIMIT 10")
        res = cur.fetchall()
        conn.close()

        text = "<b>🏆 Топ:</b>\n\n"
        for i, r in enumerate(res, 1):
            text += f"{i}. {r[0]} — {r[1]} UZS\n"

        # ← Кнопка "Назад" уже была, оставляем
        bot.edit_message_text(
            text,
            uid,
            mid,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
            )
        )

    elif call.data == "ref":
        username = bot.get_me().username
        link = f"https://t.me/{username}?start=ref_{uid}"

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (uid,))
        invited = cur.fetchone()[0]

        cur.execute("SELECT SUM(spent) FROM users WHERE referrer_id=?", (uid,))
        total = cur.fetchone()[0] or 0

        cur.execute("SELECT ref_earned, ref_balance FROM users WHERE id=?", (uid,))
        row = cur.fetchone()
        earned = row[0] if row else 0
        balance = row[1] if row else 0

        conn.close()

        # Подсчёт: сколько звёзд можно вывести (75⭐ минимум, 1 звезда ≈ 160 UZS примерно)
        # Используем условие из оригинала: вывод от 75⭐
        # Считаем 75 звёзд = 75 * 160 = 12000 UZS (можешь поменять курс)
        MIN_WITHDRAW_UZS = 12000

        text = (
            "👥 <b>Реферальная система</b>\n\n"
            f"🔗 Ваша ссылка:\n{link}\n\n"
            f"👤 Приглашено: {invited}\n"
            f"💰 Оборот рефералов: {total} UZS\n"
            f"📊 Всего заработано (2%): {earned} UZS\n"
            f"💳 Доступно к выводу: {balance} UZS\n\n"
            f"📤 Минимальный вывод: 75⭐ (~{MIN_WITHDRAW_UZS} UZS)"
        )

        kb = types.InlineKeyboardMarkup()
        # Кнопка вывода активна только если хватает баланса
        if balance >= MIN_WITHDRAW_UZS:
            kb.add(types.InlineKeyboardButton("💸 Вывести бонусы", callback_data="ref_withdraw"))
        else:
            kb.add(types.InlineKeyboardButton(f"💸 Вывод недоступен (нужно {MIN_WITHDRAW_UZS} UZS)", callback_data="ref_low"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))

        bot.edit_message_text(
            text,
            uid,
            mid,
            parse_mode="HTML",
            reply_markup=kb
        )

    # --- ВЫВОД РЕФ. БОНУСОВ ---
    elif call.data == "ref_low":
        bot.answer_callback_query(call.id, "❌ Недостаточно бонусов для вывода", show_alert=True)

    elif call.data == "ref_withdraw":
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("SELECT ref_balance FROM users WHERE id=?", (uid,))
        row = cur.fetchone()
        balance = row[0] if row else 0
        conn.close()

        MIN_WITHDRAW_UZS = 12000

        if balance < MIN_WITHDRAW_UZS:
            bot.answer_callback_query(call.id, "❌ Недостаточно бонусов", show_alert=True)
            return

        # Показываем экран подтверждения вывода
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ Подтвердить вывод", callback_data=f"ref_confirm_{balance}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="ref"))

        bot.edit_message_text(
            f"💸 <b>Вывод реферальных бонусов</b>\n\n"
            f"💳 Сумма к выводу: <b>{balance} UZS</b>\n\n"
            f"После подтверждения администратор свяжется с вами для оплаты.",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )

    elif call.data.startswith("ref_confirm_"):
        amount = int(call.data.replace("ref_confirm_", ""))

        conn = sqlite3.connect('users.db')
        cur = conn.cursor()

        # Обнуляем баланс и записываем заявку
        cur.execute("UPDATE users SET ref_balance = 0 WHERE id=?", (uid,))
        cur.execute("INSERT INTO ref_withdrawals (user_id, amount) VALUES (?, ?)", (uid, amount))
        uname = call.from_user.username or call.from_user.first_name

        conn.commit()
        conn.close()

        # Уведомляем пользователя
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="home"))
        bot.edit_message_text(
            "✅ <b>Заявка на вывод принята!</b>\n\n"
            f"💰 Сумма: {amount} UZS\n\n"
            "Администратор обработает вашу заявку в ближайшее время.",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )

        # Уведомляем админа
        bot.send_message(
            ADMIN_ID,
            f"💸 <b>Заявка на вывод реф. бонусов</b>\n\n"
            f"👤 @{uname} (ID: {uid})\n"
            f"💰 Сумма: {amount} UZS",
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ Выплачено", callback_data=f"ref_paid|{uid}"),
                types.InlineKeyboardButton("❌ Отклонить", callback_data=f"ref_reject|{uid}|{amount}")
            )
        )

    # --- АДМИН: обработка вывода ---
    elif call.data.startswith("ref_paid|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        bot.answer_callback_query(call.id, "✅ Отмечено как выплачено")
        bot.send_message(target_uid, "✅ Ваши реферальные бонусы успешно выплачены! Спасибо!")
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data.startswith("ref_reject|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        amount = int(parts[2])

        # Возвращаем баланс
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = ref_balance + ? WHERE id=?", (amount, target_uid))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "❌ Заявка отклонена, баланс возвращён")
        bot.send_message(target_uid,
            "❌ Ваша заявка на вывод была отклонена. Бонусы возвращены на баланс.\n"
            "Обратитесь в поддержку: @yngsafar"
        )
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data == "admin_balance":
        bot.answer_callback_query(call.id, f"Баланс админа: {ADMIN_BALANCE}")

    elif call.data == "delete":
        user_orders.pop(uid, None)
        bot.answer_callback_query(call.id, "🗑 Удалено")

    elif call.data == "custom":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
        msg = bot.edit_message_text(
            "✨ <b>Введите количество звёзд</b>\n\n"
            "Минимум: <b>100</b> ⭐\n"
            "Цена: <b>180 UZS</b> за звезду\n\n"
            "Пример: <i>750</i>",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )
        bot.register_next_step_handler_by_chat_id(uid, handle_custom_amount)

    elif call.data in PRICES:
        c = int(call.data.replace("p",""))
        pay_screen(uid, mid, c, PRICES[call.data])

    # --- ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ОПЛАТЫ (pay_COUNT_PRICE) ---
    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c = int(parts[1])
        p = int(parts[2])
        user_orders[uid] = {"count": c, "price": p}

        # Запрашиваем username получателя
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"p{c}"))

        msg = bot.edit_message_text(
            "📲 Введите <b>username</b> или <b>ссылку</b> на аккаунт получателя звёзд:",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )
        bot.register_next_step_handler_by_chat_id(uid, get_target_username)

    # --- ПОДТВЕРЖДЕНИЕ ОПЛАТЫ АДМИНОМ ---
    elif call.data.startswith("adm_ok|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        p = int(parts[2])
        uname = parts[3]

        update_spent(target_uid, uname, p)
        bot.answer_callback_query(call.id, "✅ Заказ подтверждён")
        bot.send_message(target_uid, "⭐ Ваш заказ подтверждён и выполнен! Спасибо за покупку!")
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data.startswith("adm_no|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        bot.answer_callback_query(call.id, "❌ Заказ отклонён")
        bot.send_message(target_uid,
            "❌ Ваш заказ был отклонён.\n"
            "Обратитесь в поддержку: @yngsafar"
        )
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

# --- ПОЛУЧЕНИЕ USERNAME ПОЛУЧАТЕЛЯ ---
def get_target_username(message):
    uid = message.from_user.id
    target = message.text.strip()

    order = user_orders.get(uid, {})
    order["target"] = target
    user_orders[uid] = order

    c = order.get("count")
    p = order.get("price")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))

    msg = bot.send_message(
        uid,
        f"🎯 Получатель: <b>{target}</b>\n"
        f"⭐ {c} звёзд — {p} UZS\n\n"
        f"📎 Отправьте <b>фото чека</b> об оплате:",
        parse_mode='HTML',
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, finish_order_with_target)

# --- СВОЯ СУММА ---
def handle_custom_amount(message):
    uid = message.from_user.id

    try:
        c = int(message.text.strip())
    except ValueError:
        msg = bot.send_message(uid,
            "❌ Введите только <b>число</b>. Попробуйте ещё раз:",
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад в магазин", callback_data="shop")
            )
        )
        bot.register_next_step_handler(msg, handle_custom_amount)
        return

    if c < 100:
        msg = bot.send_message(uid,
            "❌ Минимальное количество — <b>100 звёзд</b>. Введите ещё раз:",
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад в магазин", callback_data="shop")
            )
        )
        bot.register_next_step_handler(msg, handle_custom_amount)
        return

    p = c * 180  # 180 UZS за звезду
    pay_screen(uid, None, c, p)

# --- PAY ---
def pay_screen(uid, mid, c, p):
    text = f"💳 К оплате: {p} UZS\n⭐ {c}\n\n{CARD_DETAILS}"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))  # ← ДОБАВЛЕНО

    if mid:
        bot.edit_message_text(text, uid, mid, reply_markup=kb)
    else:
        bot.send_message(uid, text, reply_markup=kb)

# --- FINISH (НЕ ТРОГАЛ ТВОЙ КУСОК) ---
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

# --- RUN ---
if __name__ == "__main__":
    bot.infinity_polling()
