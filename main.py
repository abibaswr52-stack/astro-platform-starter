import os
import telebot
import psycopg2
import urllib.parse
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
SUPER_ADMIN_ID = 1411441331 # Тот самый Бог бота

CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

ADMIN_BALANCE = 0
user_orders = {}
BOT_STARS_BALANCE = 0

import urllib.parse

db_pass = urllib.parse.quote_plus("ibaniuz2230") # Твой текущий пароль
project_id = "aetfzeisobxgidmovrns"
db_host = "://supabase.com"

# Убрали проблемный параметр из строки
DATABASE_URL = f"postgres://postgres.{project_id}:{db_pass}@{db_host}:6543/postgres?sslmode=require"


# --- БД ---
def init_db():
    # 1. Настройки подключения
    config = {
        "host": "aws-0-ap-southeast-1.pooler.supabase.com",
        "port": "6543",
        "database": "postgres",
        "user": "postgres.aetfzeisobxgidmovrns",
        "password": "ibaniuz2230", # Если меняли пароль — впишите новый
        "sslmode": "require"
    }

    conn = None
    try:
        # 2. Пытаемся подключиться
        conn = psycopg2.connect(**config)
        cur = conn.cursor()
        
        # 3. Создаем таблицу
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                spent INTEGER DEFAULT 0,
                referrer_id BIGINT DEFAULT NULL,
                ref_earned INTEGER DEFAULT 0,
                ref_balance INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        cur.close()
        print("✅ База данных успешно подключена и настроена!")

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
    finally:
        if conn:
            conn.close()

    # Таблица заявок на вывод реф. бонусов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ref_withdrawals (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
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

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Замена INSERT OR IGNORE на синтаксис Postgres
    cur.execute("INSERT INTO users (id, username, spent) VALUES (%s, %s, 0) ON CONFLICT (id) DO NOTHING", (uid, uname))
    cur.execute("UPDATE users SET spent = spent + %s, purchases = purchases + 1, username = %s WHERE id = %s", (amount, uname, uid))

    # Коммитим сначала
    conn.commit()

    # Теперь читаем referrer_id
    cur.execute("SELECT referrer_id FROM users WHERE id=%s", (uid,))
    ref = cur.fetchone()

    if ref and ref[0]:
        bonus = int(amount * 0.05)
        cur.execute(
            "UPDATE users SET ref_earned = ref_earned + %s, ref_balance = ref_balance + %s WHERE id=%s",
            (bonus, bonus, ref[0])
        )
        conn.commit()
        # Уведомляем реферера о бонусе
        try:
            bot.send_message(
                ref[0],
                f"🎉 <b>Реферальный бонус начислен!</b>\n\n"
                f"Ваш реферал совершил покупку на <b>{amount} UZS</b>\n"
                f"💸 Ваш бонус (5%): <b>{bonus} UZS</b>",
                parse_mode='HTML'
            )
        except:
            pass

    ADMIN_BALANCE += amount
    conn.commit()
    conn.close()

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
        types.InlineKeyboardButton("❓ Частые вопросы и поддержка", callback_data="faq")
    )
    return markup

def shop_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="p1000"))
    markup.add(
        types.InlineKeyboardButton("⭐ 100 (18 000 сум)", callback_data="p100"),
        types.InlineKeyboardButton("⭐ 150 (27 000 сум)", callback_data="p150"),
        types.InlineKeyboardButton("⭐ 200 (36 000 сум)", callback_data="p200"),
        types.InlineKeyboardButton("✅ ⭐ 250 (40 000 сум)", callback_data="p250"),
        types.InlineKeyboardButton("🔥 ⭐ 300 (48 000 сум)", callback_data="p300"),
        types.InlineKeyboardButton("⭐ 350 (56 000 сум)", callback_data="p350"),
        types.InlineKeyboardButton("⭐ 400 (64 000 сум)", callback_data="p400"),
        types.InlineKeyboardButton("⭐ 450 (72 000 сум)", callback_data="p450")
    )
    markup.row(types.InlineKeyboardButton("💎 ⭐ 500 (80 000 сум)", callback_data="p500"))
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

    # ПРИВЕТСТВИЕ ДЛЯ ВЫСШЕГО АДМИНА
    if message.from_user.id == SUPER_ADMIN_ID:
        bot.send_message(message.chat.id, 
            "👑 <b>ПРИВЕТСТВУЮ, СОЗДАТЕЛЬ! БОГ ЭТОГО БОТА ВЕРНУЛСЯ!</b> 👑\n\n"
            "Ваша власть здесь абсолютна. Базы данных подчиняются вашему слову.\n"
            "Используйте команду /god_help для доступа к божественным силам.", 
            parse_mode='HTML')

    # 🔥 РЕФ КОД
    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1].replace("ref_", ""))

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            # Сначала создаём юзера если нет
            cur.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        (message.from_user.id, message.from_user.username or ""))
            conn.commit()

            # Читаем текущий referrer_id
            cur.execute("SELECT referrer_id FROM users WHERE id=%s", (message.from_user.id,))
            res = cur.fetchone()

            # Записываем реферера только если его ещё нет И это не сам реферер
            if res is not None and res[0] is None and ref_id != message.from_user.id:
                cur.execute("UPDATE users SET referrer_id=%s WHERE id=%s",
                            (ref_id, message.from_user.id))
                conn.commit()

            conn.close()
        except:
            pass

    text = (
        f"🌟 Добро пожаловать в <b>Random Stars</b>, <b>{message.from_user.first_name}</b>!\n\n"
        "💎 Быстрая покупка Telegram Stars\n"
        "⚡ Безопасно и надежно\n\n"
        f"⭐ Баланс бота: <b>{BOT_STARS_BALANCE}</b> звёзд\n"
        f"<i>(количество звёзд, доступных к покупке. Обновляется ежедневно.)</i>\n\n"
        "👇 Выберите действие:"
    )

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_kb(message.from_user.id))

# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    uid, mid = call.from_user.id, call.message.id
    bot.clear_step_handler_by_chat_id(uid)

    if call.data == "home":
        text = (
            f"🏠 <b>Главное меню</b>\n\n"
            f"⭐ Баланс бота: <b>{BOT_STARS_BALANCE}</b> звёзд\n"
            f"<i>(настраиваемый мною) — количество звёзд, доступных к покупке. Обновляется ежедневно.</i>"
        )
        bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=main_kb(uid))

    elif call.data == "shop":
        shop_text = (
            "🛒 <b>Выберите пакет:</b>\n\n"
            "💬 <i>100⭐ — 18 000 сум. Но чем больше покупаете, тем больше выгода! "
            "Например, за пакет в 500 звёзд вы покупаете намного дешевле (90 тыс → 80 тыс).</i>"
        )
        # Проверяем баланс бота
        if BOT_STARS_BALANCE <= 0:
            shop_text += "\n\n⚠️ <b>На данный момент звёзд мало. Пожалуйста, покупайте меньшее количество.</b>"
        bot.edit_message_text(shop_text, uid, mid, parse_mode='HTML', reply_markup=shop_kb())

    elif call.data == "profile":
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT username, spent, ref_earned, purchases FROM users WHERE id=%s", (uid,))
        res = cur.fetchone()
        conn.close()

        username = f"@{res[0]}" if res and res[0] else "не указан"
        spent = res[1] if res else 0
        ref_earned = res[2] if res else 0
        purchases = res[3] if res else 0

        bot.edit_message_text(
            f"👤 <b>Профиль</b>\n\n"
            f"🔤 Ник: {username}\n"
            f"🆔 ID: <code>{uid}</code>\n\n"
            f"🛍 Количество покупок: <b>{purchases}</b>\n"
            f"💰 Потрачено: <b>{spent} UZS</b>\n"
            f"💸 Заработано (рефералы): <b>{ref_earned} UZS</b>",
            uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
            )
        )

    elif call.data == "top":
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT username, spent FROM users ORDER BY spent DESC LIMIT 10")
        res = cur.fetchall()
        conn.close()

        text = "<b>🏆 Топ покупателей:</b>\n\n"
        for i, r in enumerate(res, 1):
            uname_top = f"@{r[0]}" if r[0] else "аноним"
            text += f"{i}. {uname_top} — {r[1]} UZS\n"

        bot.edit_message_text(
            text, uid, mid, parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="home")
            )
        )

    elif call.data == "ref":
        username = bot.get_me().username
        link = f"https://t.me/{username}?start=ref_{uid}"

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Гарантируем что юзер есть в БД
        cur.execute("INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    (uid, call.from_user.username or ""))
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (uid,))
        invited = cur.fetchone()[0]

        cur.execute("SELECT SUM(spent) FROM users WHERE referrer_id=%s", (uid,))
        total_tuple = cur.fetchone()
        total = total_tuple[0] if total_tuple and total_tuple[0] else 0

        cur.execute("SELECT ref_earned, ref_balance FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        earned = row[0] if row and row[0] else 0
        balance = row[1] if row and row[1] else 0

        conn.close()

        MIN_WITHDRAW_UZS = 10000

        text = (
            "👥 <b>Реферальная система</b>\n\n"
            f"🔗 Ваша ссылка:\n{link}\n\n"
            f"👤 Приглашено: {invited}\n"
            f"💰 Оборот рефералов: {total} UZS\n"
            f"📊 Всего заработано (5%): {earned} UZS\n"
            f"💳 Доступно к выводу: {balance} UZS\n\n"
            f"📤 Минимальный вывод: ~{MIN_WITHDRAW_UZS} UZS"
        )

        kb = types.InlineKeyboardMarkup()
        if balance >= MIN_WITHDRAW_UZS:
            kb.add(types.InlineKeyboardButton("💸 Вывести бонусы", callback_data="ref_withdraw"))
        else:
            kb.add(types.InlineKeyboardButton(f"💸 Вывод недоступен (нужно {MIN_WITHDRAW_UZS} UZS)", callback_data="ref_low"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))

        bot.edit_message_text(text, uid, mid, parse_mode="HTML", reply_markup=kb)

    # --- ВЫВОД РЕФ. БОНУСОВ ---
    elif call.data == "ref_low":
        bot.answer_callback_query(call.id, "❌ Недостаточно бонусов для вывода", show_alert=True)

    elif call.data == "ref_withdraw":
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT ref_balance FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        balance = row[0] if row else 0
        conn.close()

        MIN_WITHDRAW_UZS = 10000

        if balance < MIN_WITHDRAW_UZS:
            bot.answer_callback_query(call.id, "❌ Недостаточно бонусов", show_alert=True)
            return

        user_orders[uid] = {"withdraw_amount": balance}

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="ref"))

        bot.edit_message_text(
            f"💸 <b>Вывод реферальных бонусов</b>\n\n"
            f"💳 Сумма к выводу: <b>{balance} UZS</b>\n\n"
            f"📋 Введите ваши реквизиты для получения оплаты:\n\n"
            f"<i>Пример:\n"
            f"9860 1234 5678 9012\n"
            f"Иванов Иван</i>",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )
        bot.register_next_step_handler_by_chat_id(uid, handle_withdraw_requisites)

    elif call.data.startswith("ref_confirm_"):
        parts = call.data.replace("ref_confirm_", "").split("|")
        amount = int(parts[0])
        requisites = parts[1] if len(parts) > 1 else "не указаны"
        uname = call.from_user.username or call.from_user.first_name

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = 0 WHERE id=%s", (uid,))
        cur.execute("INSERT INTO ref_withdrawals (user_id, amount) VALUES (%s, %s)", (uid, amount))
        conn.commit()
        conn.close()

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="home"))
        bot.edit_message_text(
            "✅ <b>Заявка на вывод принята!</b>\n\n"
            f"💰 Сумма: <b>{amount} UZS</b>\n"
            f"💳 Реквизиты: <code>{requisites}</code>\n\n"
            "Администратор обработает вашу заявку в ближайшее время.",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )

        bot.send_message(
            ADMIN_ID,
            f"💸 <b>Заявка на вывод реф. бонусов</b>\n\n"
            f"👤 @{uname} (ID: {uid})\n"
            f"💰 Сумма: <b>{amount} UZS</b>\n"
            f"💳 Реквизиты:\n<code>{requisites}</code>",
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

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = ref_balance + %s WHERE id=%s", (amount, target_uid))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "❌ Заявка отклонена, баланс возвращён")
        bot.send_message(target_uid,
            "❌ Ваша заявка на вывод была отклонена. Бонусы возвращены на баланс.\n"
            "Обратитесь в поддержку: @yngsafar"
        )
        bot.edit_message_reply_markup(uid, mid, reply_markup=None)

    elif call.data == "faq":
        faq_text = (
            "❓ <b>Частые вопросы и поддержка</b>\n\n"
            "1. <b>Почему звёзды стоят дешево?</b>\n"
            "Звёзды пополняются с баланса бота в тг Random Games, с которого администратор поднял звёзды с помощью специального метода и большого количества приглашений реферальными ссылками.\n\n"
            "2. <b>Будет ли работать бот всегда?</b>\n"
            "Бот будет работать до тех пор, пока на балансе будут звёзды. А когда их не останется — бот предупредит всех и возможно закроется, если это станет необходимо.\n\n"
            "3. <b>Куда мне обратиться, если звёзды не пришли на аккаунт?</b>\n"
            "Если звёзды не пришли на аккаунт, заявку отклонили по ошибке или есть какие-то вопросы — пишите @RandomGamesUzbAdmin\n\n"
            "💬 <b>Прямая поддержка:</b> @RandomGamesUzbAdmin"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/RandomGamesUzbAdmin"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="home"))
        bot.edit_message_text(faq_text, uid, mid, parse_mode='HTML', reply_markup=kb)

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
        p = PRICES[call.data]
        if BOT_STARS_BALANCE > 0 and c > BOT_STARS_BALANCE:
            bot.answer_callback_query(
                call.id,
                f"⚠️ На балансе только {BOT_STARS_BALANCE} ⭐. Выберите меньшее количество.",
                show_alert=True
            )
            return
        user_orders[uid] = {"count": c, "price": p}
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
        bot.edit_message_text(
            f"⭐ <b>{c} звёзд — {p} UZS</b>\n\n"
            "📲 Введите <b>username</b> или <b>ссылку</b> на аккаунт получателя звёзд:",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )
        bot.register_next_step_handler_by_chat_id(uid, get_target_username)

    elif call.data.startswith("pay_"):
        parts = call.data.split("_")
        c = int(parts[1])
        p = int(parts[2])
        order = user_orders.get(uid, {})
        order["count"] = c
        order["price"] = p
        user_orders[uid] = order

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))
        bot.edit_message_text(
            f"💳 К оплате: <b>{p} UZS</b> за ⭐{c}\n\n"
            f"📋 Введите реквизиты вашей карты для возможного возврата\n"
            f"<i>(номер карты и имя владельца)</i>:",
            uid, mid, parse_mode='HTML', reply_markup=kb
        )
        bot.register_next_step_handler_by_chat_id(uid, get_buyer_card)

    elif call.data.startswith("adm_ok|"):
        parts = call.data.split("|")
        target_uid = int(parts[1])
        p = int(parts[2])
        uname = parts[3]

        update_spent(target_uid, uname, p)
        bot.answer_callback_query(call.id, "✅ Заказ подтверждён")
        bot.send_message(target_uid,
            "✅ <b>Ваш заказ выполнен!</b>\n\n"
            "Звёзды успешно отправлены на указанный аккаунт.\n\n"
            "Благодарим за покупку в <b>Random Stars</b>! 🌟",
            parse_mode='HTML'
        )
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

def get_target_username(message):
    uid = message.from_user.id
    target = message.text.strip()
    order = user_orders.get(uid, {})
    order["target"] = target
    user_orders[uid] = order
    c = order.get("count")
    p = order.get("price")
    pay_screen(uid, None, c, p)

def get_buyer_card(message):
    uid = message.from_user.id
    card = message.text.strip()
    order = user_orders.get(uid, {})
    order["buyer_card"] = card
    user_orders[uid] = order
    c = order.get("count")
    p = order.get("price")
    target = order.get("target", "не указан")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="shop"))

    msg = bot.send_message(
        uid,
        f"✅ Реквизиты сохранены.\n\n"
        f"🎯 Получатель: <b>{target}</b>\n"
        f"⭐ {c} звёзд — <b>{p} UZS</b>\n\n"
        f"📎 Теперь отправьте <b>фото чека</b> об оплате:",
        parse_mode='HTML',
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, finish_order_with_target)

def handle_withdraw_requisites(message):
    uid = message.from_user.id
    requisites = message.text.strip()
    order = user_orders.get(uid, {})
    amount = order.get("withdraw_amount", 0)

    if not amount:
        bot.send_message(uid, "❌ Ошибка. Попробуйте заново через рефералку.", reply_markup=main_kb(uid))
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"ref_confirm_{amount}|{requisites}"))
    kb.add(types.InlineKeyboardButton("✏️ Изменить реквизиты", callback_data="ref_withdraw"))
    kb.add(types.InlineKeyboardButton("⬅️ Отмена", callback_data="ref"))

    bot.send_message(
        uid,
        f"📋 <b>Проверьте данные:</b>\n\n"
        f"💰 Сумма: <b>{amount} UZS</b>\n"
        f"💳 Реквизиты:\n<code>{requisites}</code>\n\n"
        f"Всё верно?",
        parse_mode='HTML',
        reply_markup=kb
    )

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

    p = c * 180 
    pay_screen(uid, None, c, p)

def pay_screen(uid, mid, c, p):
    text = f"💳 К оплате: {p} UZS\n⭐ {c}\n\n{CARD_DETAILS}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"pay_{c}_{p}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="shop"))
    if mid:
        bot.edit_message_text(text, uid, mid, reply_markup=kb)
    else:
        bot.send_message(uid, text, reply_markup=kb)

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
        "📋 <b>Ваша заявка принята на рассмотрение.</b>\n\n"
        "Мы проверим поступление оплаты и в течение нескольких часов отправим вам звёзды.\n\n"
        "📌 Пожалуйста, не беспокойтесь — каждая заявка обрабатывается вручную.\n\n"
        "Если возникли вопросы: @RandomGamesUzbAdmin",
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

# --- АДМИН: обычные команды ---
@bot.message_handler(commands=['setbalance'])
def setbalance(message):
    global BOT_STARS_BALANCE
    if message.from_user.id not in [ADMIN_ID, SUPER_ADMIN_ID]:
        return
    try:
        amount = int(message.text.split()[1])
        BOT_STARS_BALANCE = amount
        bot.send_message(message.chat.id, f"✅ Баланс бота обновлён: <b>{BOT_STARS_BALANCE} ⭐</b>", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: /setbalance 5000")

@bot.message_handler(commands=['setref'])
def setref(message):
    if message.from_user.id not in [ADMIN_ID, SUPER_ADMIN_ID]:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        referrer_id = int(parts[2])

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE users SET referrer_id=%s WHERE id=%s", (referrer_id, user_id))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ Готово! Пользователю {user_id} назначен реферер {referrer_id}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: /setref USER_ID REFERRER_ID")

@bot.message_handler(commands=['checkuser'])
def checkuser(message):
    if message.from_user.id not in [ADMIN_ID, SUPER_ADMIN_ID]:
        return
    try:
        user_id = int(message.text.split()[1])
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT id, username, spent, referrer_id, ref_earned, ref_balance FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            bot.send_message(message.chat.id,
                f"👤 ID: {row[0]}\n"
                f"🔤 Username: {row[1]}\n"
                f"💰 Потрачено: {row[2]}\n"
                f"👥 Реферер: {row[3]}\n"
                f"📊 Заработано реф: {row[4]}\n"
                f"💳 Баланс реф: {row[5]}"
            )
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: /checkuser USER_ID")

# ==========================================
# БОЖЕСТВЕННЫЙ РЕЖИМ (ТОЛЬКО ДЛЯ 1411441331)
# ==========================================

@bot.message_handler(commands=['god_help'])
def god_help(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    text = (
        "👑 <b>КОМАНДЫ СОЗДАТЕЛЯ</b> 👑\n\n"
        "<code>/god_broadcast [текст]</code> — Массовая рассылка всем юзерам из БД\n"
        "<code>/god_setstat [ID] [потрачено] [покупок]</code> — Накрутить стату юзеру\n"
        "<code>/god_addrefbal [ID] [сумма]</code> — Накинуть реф. баланс юзеру напрямую\n"
        "<code>/god_sql [запрос]</code> — Прямой SQL запрос к базе (ОПАСНО!)"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['god_broadcast'])
def god_broadcast(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    text = message.text.replace("/god_broadcast", "").strip()
    if not text:
        bot.send_message(message.chat.id, "❌ Введите текст: /god_broadcast ТЕКСТ")
        return
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = cur.fetchall()
    conn.close()

    success, failed = 0, 0
    bot.send_message(message.chat.id, "🔄 Рассылка начата...")
    for u in users:
        try:
            bot.send_message(u[0], text, parse_mode='HTML')
            success += 1
        except:
            failed += 1
    
    bot.send_message(message.chat.id, f"✅ Рассылка завершена!\nУспешно: {success}\nНеудачно (заблочили): {failed}")

@bot.message_handler(commands=['god_setstat'])
def god_setstat(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        spent = int(parts[2])
        purchases = int(parts[3])

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE users SET spent = spent + %s, purchases = purchases + %s WHERE id = %s", (spent, purchases, user_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Статистика {user_id} увеличена на {spent} UZS и {purchases} покупок.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: /god_setstat [ID] [потрачено] [покупок]")

@bot.message_handler(commands=['god_addrefbal'])
def god_addrefbal(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE users SET ref_balance = ref_balance + %s, ref_earned = ref_earned + %s WHERE id = %s", (amount, amount, user_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Пользователю {user_id} начислено {amount} реф. баланса.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}\nФормат: /god_addrefbal [ID] [сумма]")

@bot.message_handler(commands=['god_sql'])
def god_sql(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    query = message.text.replace("/god_sql", "").strip()
    if not query:
        return bot.send_message(message.chat.id, "❌ Пустой запрос")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(query)
        if query.lower().startswith("select"):
            res = cur.fetchall()
            bot.send_message(message.chat.id, f"✅ Результат:\n{res}")
        else:
            conn.commit()
            bot.send_message(message.chat.id, "✅ Запрос успешно выполнен и сохранен.")
        conn.close()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ SQL Ошибка:\n{e}")

# --- RUN ---
if __name__ == "__main__":
    bot.infinity_polling()
