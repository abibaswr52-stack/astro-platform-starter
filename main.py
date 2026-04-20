import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. НАСТРОЙКА ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Бот-магазин активен!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ ---
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ВСТАВЬ СЮДА СВОЙ ID (цифрами), чтобы пользоваться админкой
ADMIN_ID = 1411441331 
ADMIN_USERNAME = "@nebulkin"

STARS_PACKS = {
    "pack_1": {"name": "⭐ 50 Звёзд", "price": "149₽", "desc": "Стартовый набор"},
    "pack_2": {"name": "🌟 500 Звёзд", "price": "990₽", "desc": "Популярный набор"},
    "pack_3": {"name": "✨ 1000 Звёзд", "price": "1850₽", "desc": "Для активных игроков"},
    "pack_4": {"name": "👑 5000 Звёзд", "price": "7900₽", "desc": "Королевский запас"}
}

# --- 3. КЛАВИАТУРЫ ---
def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛒 Магазин звёзд", callback_data="open_shop"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton("❓ Поддержка", callback_data="help")
    )
    # Если зашел админ, добавляем кнопку админки
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel"))
    return markup

def shop_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(item['name'], callback_data=k) for k, item in STARS_PACKS.items()]
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return markup

# --- 4. ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"<b>Привет, {message.from_user.first_name}!</b>\nДобро пожаловать в магазин звёзд.",
        parse_mode='HTML',
        reply_markup=main_menu(message.from_user.id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.from_user.id
    try:
        if call.data == "main_menu":
            bot.edit_message_text("<b>Главное меню:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=main_menu(uid))

        elif call.data == "open_shop":
            bot.edit_message_text("<b>Выберите пакет звёзд:</b>", uid, call.message.id, parse_mode='HTML', reply_markup=shop_menu())

        elif call.data == "profile":
            text = f"<b>👤 Профиль</b>\n\n<b>Имя:</b> {call.from_user.first_name}\n<b>ID:</b> <code>{uid}</code>\n<b>Баланс:</b> 0 ⭐"
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "help":
            text = f"<b>❓ Поддержка</b>\n\nЕсть вопросы? Напиши нашему админу:"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👨‍💻 Связаться", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data == "admin_panel" and uid == ADMIN_ID:
            text = "<b>🛠 Панель администратора</b>\n\nЗдесь вы можете управлять ботом."
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📊 Статистика (в разработке)", callback_data="none"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
            bot.edit_message_text(text, uid, call.message.id, parse_mode='HTML', reply_markup=markup)

        elif call.data in STARS_PACKS:
            item = STARS_PACKS[call.data]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💳 Купить за {item['price']}", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="open_shop"))
            bot.edit_message_text(f"<b>{item['name']}</b>\n{item['desc']}\n\nЦена: {item['price']}", uid, call.message.id, parse_mode='HTML', reply_markup=markup)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
