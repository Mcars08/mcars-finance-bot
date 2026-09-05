import os
import threading
from flask import Flask, jsonify
import telebot

# 1. Отримання токена зі змінних оточення (Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Тимчасове сховище даних (або підключи сюди свою БД / файл)
user_data = {}

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.reply_to(
        message, 
        f"Привіт! Твій ID: `{user_id}`\n\n"
        f"Твоє посилання для додатка на ПК:\n"
        f"https://mcars-finance-bot-t3na.onrender.com/get_json/{user_id}",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    # Зберігаємо повідомлення користувача
    if user_id not in user_data:
        user_data[user_id] = []
    user_data[user_id].append({"message": text})
    
    bot.reply_to(message, f"Записано: {text}")

# --- FLASK API ENDPOINTS ---

@app.route('/')
def home():
    return "Finance Bot & Web Service is Running Alive!"

@app.route('/get_json/<int:user_id>', methods=['GET'])
def get_json(user_id):
    # Повертає JSON-дані для конкретного user_id
    data = user_data.get(user_id, [])
    return jsonify(data)

# --- RUNNER ---

def run_bot():
    print("Запуск Telegram бота...")
    bot.infinity_polling(skip_pending_webhooks=True)

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці, щоб Flask не блокувався
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask вебсервера на порту від Render (або 5000 за замовчуванням)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
