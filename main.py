import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. НАСТРОЙКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Shop is Online"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ БОТА ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# НАСТРОЙКИ
ADMIN_ID = 123456789  # ВСТАВЬ СВОЙ ID
CARD_DETAILS = "9860 1001 2780 5412\nSafarbek K."

# ЦЕНЫ
STARS_PACKS = {
    "special": {"name": "🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ", "price": 145000, "count": 1000},
    "p100": {"name": "⭐ 100", "price": 18000, "count": 100},
    "p150": {"name": "⭐ 150", "price": 27000, "count": 150},
    "p200": {"name": "⭐ 200", "price": 36000, "count": 200},
    "p250": {"name": "⭐ 250", "price": 40000, "count": 250},
    "p300": {"name": "⭐ 300", "price": 48000, "count": 300},
    "p350": {"name": "⭐ 350", "price": 56000, "count": 350},
    "p400": {"name": "⭐ 400", "price": 64000, "count": 400},
    "p450": {"name": "⭐ 450", "price": 72000, "count": 450},
    "p500": {"name": "⭐ 500", "price": 80000, "count": 500}
}

# --- 3. КЛАВИАТУРЫ ---

def main_menu_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин звёзд", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def shop_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Спецпредложение сверху
    markup.row(types.InlineKeyboardButton("🎁 ОСОБОЕ ПРЕДЛОЖЕНИЕ (1000 шт)", callback_data="special"))
    
    # Кнопки товаров
    btns = []
    for k, v in STARS_PACKS.items():
        if k == "special": continue
        prefix = "✅ " if k == "p250" else "🔥 " if k == "p300" else "💎 " if k == "p500" else ""
        btns.append(types.InlineKeyboardButton(f"{prefix}{v['name']} — {v['price']:,} UZS".replace(',', ' '), callback_data=k))
    
    markup.add(*btns) # Здесь было .insert, теперь исправлено на .add
    markup.row(types.InlineKeyboardButton("✨ ВВЕСТИ СВОЮ СУММУ", callback_data="ask_custom"))
    markup.row(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return markup

# --- 4. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"<b>Привет, {message.from_user.first_name}!</b>\nВыберите раздел:", 
                     parse_mode='HTML', reply_markup=main_menu_markup(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    mid = call.message.id

    if call.data == "main_menu":
        bot.edit_message_text("<b>Главное меню:</b>", uid, mid, parse_mode='HTML', reply_markup=main_menu_markup(uid))
    
    elif call.data == "open_shop":
        bot.edit_message_text("<b>Выберите количество звёзд:</b>", uid, mid, parse_mode='HTML', reply_markup=shop_menu_markup())

    elif call.data == "ask_custom":
        msg = bot.edit_message_text("<b>Введите количество звёзд (число):</b>", uid, mid, parse_mode='HTML', 
                                    reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Отмена", callback_data="open_shop")))
        bot.register_next_step_handler(msg, process_custom_amount)

    elif call.data in STARS_PACKS:
        item = STARS_PACKS[call.data]
        show_payment_details(uid, mid, item['count'], item['price'])

    elif call.data.startswith("paid_"):
        _, amount, price = call.data.split("_")
        ask_for_receipt(uid, mid, amount, price)

    elif call.data == "profile":
        bot.edit_message_text(f"<b>👤 Профиль</b>\nID: <code>{uid}</code>\nБаланс: 0 ⭐", uid, mid, 
                              parse_mode='HTML', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")))

# --- ЛОГИКА ОПЛАТЫ ---

def show_payment_details(uid, mid, amount, price):
    text = (
        f"<b>💳 Оплата: {amount} ⭐</b>\n"
        f"──────────────────\n"
        f"💰 <b>Сумма:</b> <code>{price:,} UZS</code>\n"
        f"🏦 <b>Реквизиты:</b>\n<code>{CARD_DETAILS}</code>\n"
        f"──────────────────\n"
        f"После оплаты нажмите кнопку ниже:"
    ).replace(',', ' ')
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{amount}_{price}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="open_shop"))
    
    bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=markup)

def ask_for_receipt(uid, mid, amount, price):
    text = (
        "<b>🧾 Подтверждение оплаты</b>\n\n"
        "Пожалуйста, предоставьте чек за оплату.\n"
        "Нажмите кнопку ниже, чтобы отправить фото."
    )
    # Кнопка для вида, но бот просто будет ждать фото после этого текста
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📸 Предоставить чек (отправьте фото)", callback_data="ignore"))
    
    bot.edit_message_text(text, uid, mid, parse_mode='HTML', reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(uid, process_final_step, amount, price)

def process_final_step(message, amount, price):
    uid = message.from_user.id
    
    if message.content_type != 'photo':
        msg = bot.send_message(uid, "⚠️ Пожалуйста, отправьте <b>фотографию</b> (чек)!")
        bot.register_next_step_handler(msg, process_final_step, amount, price)
        return

    # Финальный ответ пользователю
    bot.send_message(uid, "✅ <b>Ваша заявка принята и будет обработана админами, ожидайте ответ!</b>", 
                     parse_mode='HTML', reply_markup=main_menu_markup(uid))

    # Уведомление админу
    admin_text = (
        f"🚀 <b>НОВЫЙ ЗАКАЗ!</b>\n"
        f"──────────────────\n"
        f"👤 <b>Клиент:</b> @{message.from_user.username}\n"
        f"📦 <b>Товар:</b> {amount} ⭐\n"
        f"💰 <b>Цена:</b> {price} UZS\n"
        f"──────────────────"
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id)

# --- КАЛЬКУЛЯТОР ---
def process_custom_amount(message):
    uid = message.from_user.id
    try:
        amount = int(message.text)
        if amount < 100:
            bot.send_message(uid, "❌ Минимум 100 ⭐", reply_markup=shop_menu_markup())
            return
        price = amount * (160 if amount >= 250 else 180)
        show_payment_details(uid, None, amount, price) # Передаем None, так как это новое сообщение
    except:
        bot.send_message(uid, "⚠️ Введите число.", reply_markup=shop_menu_markup())

if __name__ == "__main__":
    bot.infinity_polling()
