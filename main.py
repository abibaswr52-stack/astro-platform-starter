import os
import telebot
import psycopg2
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

ADMIN_ID       = 1001209009
SUPER_ADMIN_ID = 1411441331

CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

ADMIN_BALANCE     = 0
user_orders       = {}
BOT_STARS_BALANCE = 0

# --- ПОДКЛЮЧЕНИЕ К SUPABASE ---
# Пароль передаётся как отдельный параметр — спецсимволы не нужно экранировать
DB_CONFIG = {
    "host":     "aws-1-ap-southeast-1.pooler.supabase.com",
    "port":     "5432",
    "database": "postgres",
    "user":     "postgres.aetfzeisobxgidmovrns",
    "password": "ibaniuz2230",
    "sslmode":  "require"
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# --- ИНИЦИАЛИЗАЦИЯ БД (исправлено: всё в одном try/finally) ---
def init_db():
    conn = get_conn()
    cur  = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id          BIGINT PRIMARY KEY,
                username    TEXT,
                spent       INTEGER DEFAULT 0,
                referrer_id BIGINT  DEFAULT NULL,
                ref_earned  INTEGER DEFAULT 0,
                ref_balance INTEGER DEFAULT 0,
                purchases   INTEGER DEFAULT 0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS ref_withdrawals (
                id      SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount  INTEGER,
                status  TEXT DEFAULT 'pending'
            )
        ''')
        conn.commit()
        print("✅ Таблицы созданы успешно!")
    except Exception as e:
        print(f"❌ Ошибка init_db: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

init_db()

# --- ЦЕНЫ (новые по тетрадке) ---
PRICES = {
    "p100": 15000, "p150": 21000, "p200": 28000, "p250": 34500,
    "p300": 41000, "p350": 48000, "p400": 55000, "p450": 62000,
    "p500": 69000, "p1000": 138000
}

def calc_price(stars):
    """Формула: stars * 150 - 8%"""
    raw = stars * 150
    return int(raw - raw * 0.08)

# --- ОБНОВЛЕНИЕ ТРАТ + РЕФ БОНУС ---
def update_spent(uid, uname, amount):
    global ADMIN_BALANCE
    conn = get_conn()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (id, username, spent, purchases)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (id) DO UPDATE
            SET spent     = users.spent + EXCLUDED.spent,
                purchases = users.purchases + 1,
                username  = EXCLUDED.username
        """, (uid, uname, amount))
        conn.commit()

        cur.execute("SELECT referrer_id FROM users WHERE id=%s", (uid,))
        ref = cur.fetchone()
        if ref and ref[0]:
            bonus = int(amount * 0.05)
            cur.execute("""
                UPDATE users
                SET ref_earned  = ref_earned  + %s,
                    ref_balance = ref_balance + %s
                WHERE id = %s
            """, (bonus, bonus, ref[0]))
            conn.commit()
            try:
                bot.send_message(ref[0],
                    f"🎉 <b>Реферальный бонус начислен!</b>\n\n"
                    f"Ваш реферал купил на <b>{amount} UZS</b>\n"
                    f"💸 Ваш бонус (5%): <b>{bonus} UZS</b>",
                    parse_mode='HTML')
            except:
                pass
        ADMIN_BALANCE += amount
    except Exception as e:
        print(f"❌ update_spent: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --- КЛАВИАТУРЫ ---
def main_kb(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин",  callback_data="shop"),
        types.InlineKeyboardButton("👤 Профиль",  callback_data="profile")
    )
    markup.add(
        types.InlineKeyboardButton("🏆 Топ",       callback_data="top"),
        types.InlineKeyboardButton("👥 Рефералка", callback_data="ref")
    )
    markup.add(types.InlineKeyboardButton("❓ Частые вопросы и поддержка", callback_data="faq"))
    return markup

def shop_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="p1000"))
    markup.add(
        types.InlineKeyboardButton("⭐ 100 (15 000 сум)",    callback_data="p100"),
        types.InlineKeyboardButton("⭐ 150 (21 000 сум)",    callback_data="p150"),
        types.InlineKeyboardButton("⭐ 200 (28 000 сум)",    callback_data="p200"),
        types.InlineKeyboardButton("✅ ⭐ 250 (34 500 сум)", callback_data="p250"),
        types.InlineKeyboardButton("🔥 ⭐ 300 (41 000 сум)", callback_data="p300"),
        types.InlineKeyboardButton("⭐ 350 (48 000 сум)",    callback_data="p350"),
        types.InlineKeyboardButton("⭐ 400 (55 000 сум)",    callback_data="p400"),
        types.InlineKeyboardButton("⭐ 450 (62 000 сум)",    callback_data="p450"),
    )
    markup.row(types.InlineKeyboardButton("💫 ⭐ 500 (69 000 сум)", callback_data="p500"))
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЁ КОЛИЧЕСТВО", callback_data="custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
    return markup

# --- /start ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id

    if uid == SUPER_ADMIN_ID:
        bot.send_message(uid,
            "👑 <b>ПРИВЕТСТВУЮ, СОЗДАТЕЛЬ! БОГ ЭТОГО БОТА ВЕРНУЛСЯ!</b> 👑\n\n"
            "Ваша власть здесь абсолютна. Базы данных подчиняются вашему слову.\n\n"
            "⚙️ <b>Обычные команды:</b>\n"
            "/setbalance — баланс бота\n"
            "/setref — привязать реферера\n"
            "/checkuser — инфо о юзере\n\n"
            "👑 <b>Божественные команды:</b>\n"
            "/god_help — полный список команд создателя",
            parse_mode='HTML', reply_markup=main_kb(uid))
        return

    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1].replace("ref_", ""))
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        (uid, message.from_user.username or ""))
            conn.commit()
            cur.execute("SELECT referrer_id FROM users WHERE id=%s", (uid,))
            res = cur.fetchone()
            if res and res[0] is None and ref_id != uid:
                cur.execute("UPDATE users SET referrer_id=%s WHERE id=%s", (ref_id, uid))
                conn.commit()
            cur.close(); conn.close()
        except:
            pass

    text = (
        f"🌟 Добро пожаловать в <b>Random Stars</b>, <b>{message.from_user.first_name}</b>!\n\n"
        "💎 Быстрая покупка Telegram Stars\n"
        "⚡ Безопасно и надёжно\n\n"
        f"⭐ Баланс бота: <b>{BOT_STARS_BALANCE}</b> звёзд\n"
        "<i>(количество звёзд, доступных к покупке. Обновляется ежедневно.)</i>\n\n"
        "👇 Выберите действие:"
    )
    bot.send_message(uid, text, parse_mode='HTML', reply_markup=main_kb(uid))

# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        bot.edit_message_text(
            f"🏠 <b>Главное меню</b>\n\n"
            f"⭐ Баланс бота: <b>{BOT_STARS_BALANCE}</b> звёзд\n"
            "<i>(количество звёзд, доступных к покупке. Обновляется ежедневно.)</i>",
            uid, mid, parse_mode='HTML', reply_markup=main_kb(uid))

    elif call.data == "shop":
        shop_text = (
            "🛒 <b>Выберите пакет:</b>\n\n"
            "💬 <i>Чем больше покупаете — тем выгоднее!\n"
            "Формула: кол-во × 150 сум − 8% скидка.</i>"
        )
        if BOT_STARS_BALANCE <= 0:
            shop_text += "\n\n⚠️ <b>Звёзд мало. Покупайте меньшее количество.</b>"
        bot.edit_message_text(shop_text, uid, mid, parse_mode='HTML', reply_markup=shop_kb())

    elif call.data == "profile":
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT username, spent, ref_earned, purchases FROM users WHERE id=%s", (uid,))
        res = cur.fetchone()
        cur.close(); conn.close()
        uname_str = f"@{res[0]}" if res and res[0] else "не указан"
        spent     = res[1] if res else 0
        ref_earned= res[2] if res else 0
        purchases = res[3] if res else 0
        bot.edit_message_text(
            f"👤 <b>Профиль</b>\n\n"
            f"🔤 Ник: {uname_str}\n"
            f"🆔 ID: <code>{uid}</code>\n\n"
            f"🛍 Покупок: <b>{purchases}</b>\n"
            f"💰 Потрачено: <b>{spent} UZS</b>\n"
            f"💸 Заработано (рефералы): <b>{ref_earned} UZS</b>",
            uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))

    elif call.data == "top":
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users ORDER BY spent DESC LIMIT 10")
        res = cur.fetchall()
        cur.close(); conn.close()
        text = "<b>🏆 Топ покупателей:</b>\n\n"
        for i, r in enumerate(res, 1):
            text += f"{i}. {'@'+r[0] if r[0] else 'аноним'} — {r[1]} UZS\n"
        bot.edit_message_text(text, uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")))

    elif call.data == "ref":
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start=ref_{uid}"
        conn = get_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (uid, call.from_user.username or ""))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (uid,))
        invited = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(spent), 0) FROM users WHERE referrer_id=%s", (uid,))
        total = cur.fetchone()[0]
        cur.execute("SELECT ref_earned, ref_balance FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        earned = row[0] if row else 0
        balance= row[1] if row else 0
        cur.close(); conn.close()
        MIN = 10000
        kb = types.InlineKeyboardMarkup()
        if balance >= MIN:
            kb.add(types.InlineKeyboardButton("💸 Вывести бонусы", callback_data="ref_withdraw"))
        else:
            kb.add(types.InlineKeyboardButton(f"💸 Вывод недоступен (нужно {MIN} UZS)", callback_data="ref_low"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
        bot.edit_message_text(
            "👥 <b>Реферальная система</b>\n\n"
            f"🔗 Ваша ссылка:\n{link}\n\n"
            f"👤 Приглашено: {invited}\n"
            f"💰 Оборот рефералов: {total} UZS\n"
            f"📊 Всего заработано (5%): {earned} UZS\n"
            f"💳 Доступно к выводу: {balance} UZS\n\n"
            f"📤 Минимальный вывод: ~{MIN} UZS",
            uid, mid, parse_mode="HTML", reply_markup=kb)

    elif call.data == "ref_low":
        bot.answer_callback_query(call.id, "❌ Недостаточно бонусов для вывода", show_alert=True)

    elif call.data == "ref_withdraw":
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT ref_balance FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        balance = row[0] if row else 0
        cur.close(); conn.close()
        if balance < 10000:
            bot.answer_callback_query(call.id, "❌ Недостаточно бонусов", show_alert=True)
            return
        user_orders[uid] = {"withdraw_amount": balance}
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="ref"))
        bot.edit_message_text(
            f"💸 <b>Вывод реферальных бонусов</b>\n\n"
            f"💳 Сумма к выводу: <b>{balance} UZS</b>\n\n"
            f"📋 Введите реквизиты для получения:\n"
            f"<i>Пример:\n9860 1234 5678 9012\nИванов Иван</i>",
            uid, mid, parse_mode='HTML', reply_markup=kb)
        bot.register_next_step_handler_by_chat_id(uid, handle_withdraw_requisites)

    elif call.data.startswith("ref_confirm_"):
        parts = call.data.replace("ref_confirm_", "").split("|")
        amount = int(parts[0])
        requisites = parts[1] if len(parts) > 1 else "не указаны"
        uname = call.from_user.username or call.from_user.first_name
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = 0 WHERE id=%s", (uid,))
        cur.execute("INSERT INTO ref_withdrawals (user_id, amount) VALUES (%s, %s)", (uid, amount))
        conn.commit(); cur.close(); conn.close()
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="home"))
        bot.edit_message_text(
            "✅ <b>Заявка на вывод принята!</b>\n\n"
            f"💰 Сумма: <b>{amount} UZS</b>\n"
            f"💳 Реквизиты: <code>{requisites}</code>\n\n"
            "Администратор обработает вашу заявку в ближайшее время.",
            uid, mid, parse_mode='HTML', reply_markup=kb)
        adm_kb = types.InlineKeyboardMarkup()
        adm_kb.add(
            types.InlineKeyboardButton("✅ Выплачено", callback_data=f"ref_paid|{uid}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"ref_reject|{uid}|{amount}"))
        for admin in [ADMIN_ID, SUPER_ADMIN_ID]:
            try:
                bot.send_message(admin,
                    f"💸 <b>Заявка на вывод реф. бонусов</b>\n\n"
                    f"👤 @{uname} (ID: {uid})\n"
                    f"💰 Сумма: <b>{amount} UZS</b>\n"
                    f"💳 Реквизиты:\n<code>{requisites}</code>",
                    parse_mode='HTML', reply_markup=adm_kb)
            except:
                pass

    elif call.data.startswith("ref_paid|"):
        target_uid = int(call.data.split("|")[1])
        bot.answer_callback_query(call.id, "✅ Отмечено как выплачено")
        bot.send_message(target_uid, "✅ Ваши реферальные бонусы успешно выплачены! Спасибо!")
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data.startswith("ref_reject|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        amount = int(parts[2])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = ref_balance + %s WHERE id=%s", (amount, target_uid))
        conn.commit(); cur.close(); conn.close()
        bot.answer_callback_query(call.id, "❌ Заявка отклонена, баланс возвращён")
        bot.send_message(target_uid,
            "❌ Заявка на вывод отклонена. Бонусы возвращены.\nПоддержка: @RandomGamesUzbAdmin")
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data == "faq":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/RandomGamesUzbAdmin"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
        bot.edit_message_text(
            "❓ <b>Частые вопросы и поддержка</b>\n\n"
            "1. <b>Почему звёзды стоят дешево?</b>\n"
            "Звёзды пополняются с баланса бота в тг Random Games, с которого администратор поднял звёзды с помощью специального метода и большого количества приглашений реферальными ссылками.\n\n"
            "2. <b>Будет ли работать бот всегда?</b>\n"
            "Бот будет работать до тех пор, пока на балансе будут звёзды. А когда их не останется — бот предупредит всех.\n\n"
            "3. <b>Звёзды не пришли — что делать?</b>\n"
            "Пишите @RandomGamesUzbAdmin\n\n"
            "💬 <b>Прямая поддержка:</b> @RandomGamesUzbAdmin",
            uid, mid, parse_mode='HTML', reply_markup=kb)

    elif call.data == "delete":
        user_orders.pop(uid, None)
        bot.answer_callback_query(call.id, "🗑 Удалено")

    elif call.data == "custom":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
        bot.edit_message_text(
            "✨ <b>Введите количество звёзд</b>\n\n"
            "Минимум: <b>100</b> ⭐\n"
            "Формула: кол-во × 150 сум − 8% скидка\n\n"
            "<i>Пример: 750 → 750×150=112 500 − 8% = 103 500 сум</i>",
            uid, mid, parse_mode='HTML', reply_markup=kb)
        bot.register_next_step_handler_by_chat_id(uid, handle_custom_amount)

    elif call.data in PRICES:
        c = int(call.data.replace("p", ""))
        p = PRICES[call.data]
        if BOT_STARS_BALANCE > 0 and c > BOT_STARS_BALANCE:
            bot.answer_callback_query(call.id,
                f"⚠️ На балансе только {BOT_STARS_BALANCE} ⭐. Выберите меньше.", show_alert=True)
            return
        user_orders[uid] = {"count": c, "price": p}
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
        bot.edit_message_text(
            f"⭐ <b>{c} звёзд — {p} UZS</b>\n\n"
            "📲 Введите <b>username</b> или <b>ссылку</b> на аккаунт получателя звёзд:",
            uid, mid, parse_mode='HTML', reply_markup=kb)
        bot.register_next_step_handler_by_chat_id(uid, get_target_username)

    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c = int(parts[1]); p = int(parts[2])
        order = user_orders.get(uid, {})
        order["count"] = c; order["price"] = p
        user_orders[uid] = order
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⏭ Пропустить", callback_data=f"skip_card_{c}_{p}"))
        kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))
        bot.edit_message_text(
            f"💳 К оплате: <b>{p} UZS</b> за ⭐{c}\n\n"
            f"📋 Введите реквизиты вашей карты\n"
            f"<i>(номер карты и имя — для возможного возврата)</i>\n\n"
            f"Или нажмите <b>Пропустить</b>:",
            uid, mid, parse_mode='HTML', reply_markup=kb)
        bot.register_next_step_handler_by_chat_id(uid, get_buyer_card)

    elif call.data.startswith("skip_card_"):
        parts = call.data.split("_")
        c = int(parts[2]); p = int(parts[3])
        order = user_orders.get(uid, {})
        order["buyer_card"] = "не указаны"
        user_orders[uid] = order
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))
        msg = bot.send_message(uid,
            f"🎯 Получатель: <b>{order.get('target','не указан')}</b>\n"
            f"⭐ {c} звёзд — <b>{p} UZS</b>\n\n"
            f"📎 Отправьте <b>фото чека</b> об оплате:",
            parse_mode='HTML', reply_markup=kb)
        bot.register_next_step_handler(msg, finish_order_with_target)

    elif call.data.startswith("adm_ok|"):
        parts = call.data.split("|")
        target_uid = int(parts[1]); p = int(parts[2]); uname = parts[3]
        update_spent(target_uid, uname, p)
        bot.answer_callback_query(call.id, "✅ Заказ подтверждён")
        bot.send_message(target_uid,
            "✅ <b>Ваш заказ выполнен!</b>\n\n"
            "Звёзды успешно отправлены на указанный аккаунт.\n\n"
            "Благодарим за покупку в <b>Random Stars</b>! 🌟", parse_mode='HTML')
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data.startswith("adm_no|"):
        target_uid = int(call.data.split("|")[1])
        bot.answer_callback_query(call.id, "❌ Заказ отклонён")
        bot.send_message(target_uid, "❌ Ваш заказ отклонён.\nПоддержка: @yngsafar")
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

# --- ШАГИ ПОКУПКИ ---
def get_target_username(message):
    uid = message.from_user.id
    order = user_orders.get(uid, {})
    order["target"] = message.text.strip()
    user_orders[uid] = order
    pay_screen(uid, None, order.get("count"), order.get("price"))

def get_buyer_card(message):
    uid = message.from_user.id
    order = user_orders.get(uid, {})
    order["buyer_card"] = message.text.strip()
    user_orders[uid] = order
    c = order.get("count"); p = order.get("price"); target = order.get("target", "не указан")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))
    msg = bot.send_message(uid,
        f"✅ Реквизиты сохранены.\n\n"
        f"🎯 Получатель: <b>{target}</b>\n"
        f"⭐ {c} звёзд — <b>{p} UZS</b>\n\n"
        f"📎 Отправьте <b>фото чека</b> об оплате:",
        parse_mode='HTML', reply_markup=kb)
    bot.register_next_step_handler(msg, finish_order_with_target)

def handle_withdraw_requisites(message):
    uid = message.from_user.id
    requisites = message.text.strip()
    order = user_orders.get(uid, {})
    amount = order.get("withdraw_amount", 0)
    if not amount:
        bot.send_message(uid, "❌ Ошибка. Попробуйте через рефералку.", reply_markup=main_kb(uid))
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"ref_confirm_{amount}|{requisites}"))
    kb.add(types.InlineKeyboardButton("✏️ Изменить", callback_data="ref_withdraw"))
    kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="ref"))
    bot.send_message(uid,
        f"📋 <b>Проверьте данные:</b>\n\n"
        f"💰 Сумма: <b>{amount} UZS</b>\n"
        f"💳 Реквизиты:\n<code>{requisites}</code>\n\nВсё верно?",
        parse_mode='HTML', reply_markup=kb)

def handle_custom_amount(message):
    uid = message.from_user.id
    try:
        c = int(message.text.strip())
    except ValueError:
        msg = bot.send_message(uid, "❌ Введите только <b>число</b>:", parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="shop")))
        bot.register_next_step_handler(msg, handle_custom_amount)
        return
    if c < 100:
        msg = bot.send_message(uid, "❌ Минимум — <b>100 звёзд</b>. Введите ещё раз:", parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="shop")))
        bot.register_next_step_handler(msg, handle_custom_amount)
        return
    if BOT_STARS_BALANCE > 0 and c > BOT_STARS_BALANCE:
        msg = bot.send_message(uid,
            f"⚠️ На балансе только <b>{BOT_STARS_BALANCE} ⭐</b>. Введите меньше:", parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="shop")))
        bot.register_next_step_handler(msg, handle_custom_amount)
        return
    p = calc_price(c)
    user_orders[uid] = {"count": c, "price": p}
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
    msg = bot.send_message(uid,
        f"⭐ <b>{c} звёзд — {p} UZS</b>\n\n"
        "📲 Введите <b>username</b> или <b>ссылку</b> на аккаунт получателя:",
        parse_mode='HTML', reply_markup=kb)
    bot.register_next_step_handler(msg, get_target_username)

def pay_screen(uid, mid, c, p):
    text = f"💳 К оплате: <b>{p} UZS</b>\n⭐ {c} звёзд\n\n{CARD_DETAILS}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
    if mid:
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)

def finish_order_with_target(message):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Нужен фото чек. Попробуйте ещё раз:")
        bot.register_next_step_handler(msg, finish_order_with_target)
        return
    uid = message.from_user.id
    uname = message.from_user.username or message.from_user.first_name
    order = user_orders.get(uid, {})
    c = order.get("count"); p = order.get("price")
    target = order.get("target", "не указан"); card = order.get("buyer_card", "не указаны")
    bot.send_message(uid,
        "📋 <b>Ваша заявка принята на рассмотрение.</b>\n\n"
        "Мы проверим поступление оплаты и в течение нескольких часов отправим звёзды.\n\n"
        "📌 Каждая заявка обрабатывается вручную.\n\n"
        "Если возникли вопросы: @RandomGamesUzbAdmin",
        parse_mode='HTML', reply_markup=main_kb(uid))
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_ok|{uid}|{p}|{uname}"))
    kb.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no|{uid}"))
    caption = f"👤 @{uname} (ID: {uid})\n🎯 {target}\n⭐ {c}\n💰 {p} UZS\n💳 Карта: {card}"
    for admin in [ADMIN_ID, SUPER_ADMIN_ID]:
        try:
            bot.send_photo(admin, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        except:
            pass

# --- ОБЫЧНЫЕ ADMIN КОМАНДЫ ---
def is_admin(uid):
    return uid in (ADMIN_ID, SUPER_ADMIN_ID)

@bot.message_handler(commands=['setbalance'])
def setbalance(message):
    global BOT_STARS_BALANCE
    if not is_admin(message.from_user.id): return
    try:
        BOT_STARS_BALANCE = int(message.text.split()[1])
        bot.send_message(message.chat.id,
            f"✅ Баланс бота: <b>{BOT_STARS_BALANCE} ⭐</b>", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Формат: /setbalance 5000\n{e}")

@bot.message_handler(commands=['setref'])
def setref(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        user_id = int(parts[1]); referrer_id = int(parts[2])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET referrer_id=%s WHERE id=%s", (referrer_id, user_id))
        conn.commit(); cur.close(); conn.close()
        bot.send_message(message.chat.id, f"✅ Пользователю {user_id} назначен реферер {referrer_id}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Формат: /setref USER_ID REFERRER_ID\n{e}")

@bot.message_handler(commands=['checkuser'])
def checkuser(message):
    if not is_admin(message.from_user.id): return
    try:
        user_id = int(message.text.split()[1])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT id, username, spent, purchases, referrer_id, ref_earned, ref_balance FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            bot.send_message(message.chat.id,
                f"👤 ID: {row[0]}\n🔤 @{row[1]}\n"
                f"💰 Потрачено: {row[2]} UZS\n🛍 Покупок: {row[3]}\n"
                f"👥 Реферер: {row[4]}\n📊 Реф заработано: {row[5]}\n💳 Реф баланс: {row[6]}")
        else:
            bot.send_message(message.chat.id, "❌ Не найден")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Формат: /checkuser USER_ID\n{e}")

# --- КОМАНДЫ БОГА ---
@bot.message_handler(commands=['god_help'])
def god_help(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    bot.send_message(message.chat.id,
        "👑 <b>КОМАНДЫ СОЗДАТЕЛЯ</b> 👑\n\n"
        "<code>/god_stats</code> — статистика бота\n"
        "<code>/god_broadcast [текст]</code> — рассылка всем\n"
        "<code>/god_setstat [ID] [потрачено] [покупок]</code> — накрутить стату\n"
        "<code>/god_addrefbal [ID] [сумма]</code> — накинуть реф. баланс\n"
        "<code>/god_allorders</code> — все заявки на вывод\n"
        "<code>/god_sql [запрос]</code> — прямой SQL (ОПАСНО!)",
        parse_mode='HTML')

@bot.message_handler(commands=['god_stats'])
def god_stats(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(spent), 0) FROM users")
    total_revenue = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ref_withdrawals WHERE status='pending'")
    pending = cur.fetchone()[0]
    cur.close(); conn.close()
    bot.send_message(message.chat.id,
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"💰 Общий оборот: <b>{total_revenue} UZS</b>\n"
        f"⭐ Баланс бота: <b>{BOT_STARS_BALANCE}</b>\n"
        f"⏳ Заявок на вывод: <b>{pending}</b>",
        parse_mode='HTML')

@bot.message_handler(commands=['god_broadcast'])
def god_broadcast(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    text = message.text.replace("/god_broadcast", "").strip()
    if not text:
        bot.send_message(message.chat.id, "❌ Формат: /god_broadcast ТЕКСТ"); return
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = cur.fetchall(); cur.close(); conn.close()
    ok = fail = 0
    bot.send_message(message.chat.id, "🔄 Рассылка начата...")
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>Сообщение от администрации:</b>\n\n{text}", parse_mode='HTML')
            ok += 1
        except:
            fail += 1
    bot.send_message(message.chat.id, f"✅ Готово!\n📨 Отправлено: {ok}\n❌ Ошибок: {fail}")

@bot.message_handler(commands=['god_setstat'])
def god_setstat(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    try:
        parts = message.text.split()
        user_id = int(parts[1]); spent = int(parts[2]); purchases = int(parts[3])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET spent=spent+%s, purchases=purchases+%s WHERE id=%s",
                    (spent, purchases, user_id))
        conn.commit(); cur.close(); conn.close()
        bot.send_message(message.chat.id, f"✅ Стата {user_id} увеличена.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Формат: /god_setstat [ID] [потрачено] [покупок]\n{e}")

@bot.message_handler(commands=['god_addrefbal'])
def god_addrefbal(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    try:
        parts = message.text.split()
        user_id = int(parts[1]); amount = int(parts[2])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance=ref_balance+%s, ref_earned=ref_earned+%s WHERE id=%s",
                    (amount, amount, user_id))
        conn.commit(); cur.close(); conn.close()
        bot.send_message(message.chat.id, f"✅ Начислено {amount} UZS пользователю {user_id}.")
        try: bot.send_message(user_id, f"🎁 Вам начислен бонус: <b>{amount} UZS</b>!", parse_mode='HTML')
        except: pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Формат: /god_addrefbal [ID] [сумма]\n{e}")

@bot.message_handler(commands=['god_allorders'])
def god_allorders(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT rw.id, rw.user_id, u.username, rw.amount, rw.status
        FROM ref_withdrawals rw LEFT JOIN users u ON u.id=rw.user_id
        ORDER BY rw.id DESC LIMIT 20
    """)
    rows = cur.fetchall(); cur.close(); conn.close()
    if not rows:
        bot.send_message(message.chat.id, "📭 Заявок нет"); return
    text = "📋 <b>Последние 20 заявок:</b>\n\n"
    for r in rows:
        text += f"#{r[0]} | @{r[2]} (ID:{r[1]}) | {r[3]} UZS | {r[4]}\n"
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['god_sql'])
def god_sql(message):
    if message.from_user.id != SUPER_ADMIN_ID: return
    query = message.text.replace("/god_sql", "").strip()
    if not query:
        bot.send_message(message.chat.id, "❌ Пустой запрос"); return
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute(query)
        if query.strip().lower().startswith("select"):
            res = cur.fetchall()
            bot.send_message(message.chat.id, f"✅ Результат:\n<code>{res}</code>", parse_mode='HTML')
        else:
            conn.commit()
            bot.send_message(message.chat.id, "✅ Запрос выполнен.")
        cur.close(); conn.close()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ SQL Ошибка:\n{e}")

# --- RUN ---
if __name__ == "__main__":
    bot.infinity_polling()
