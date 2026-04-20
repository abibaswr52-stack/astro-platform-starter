import os
from flask import Flask
from threading import Thread
import telebot # Или aiogram, смотря что ты используешь

# 1. ЧАСТЬ ДЛЯ RENDER (ЧТОБЫ НЕ ВЫКЛЮЧАЛСЯ)
app = Flask('')

@app.route('/')
def home():
    return "Бот запущен и работает!"

def run():
    # Render сам подставит нужный порт
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. ТВОЙ БОТ
# Берем токен из настроек Render (Environment Variables), которые мы уже ввели
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я работаю 24/7 на хостинге!")

# Тут добавь остальной свой код бота...

# 3. ЗАПУСК ВСЕГО ВМЕСТЕ
if __name__ == "__main__":
    keep_alive() # Запускаем веб-сервер в фоне
    print("Бот погнал!")
    bot.infinity_polling() # Запускаем бота
