import os
import json
import threading
from flask import Flask, jsonify
import telebot

# 1. Отримання токена зі змінних оточення (Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

# --- ФУНКЦІЇ ДЛЯ РОБОТИ З ФАЙЛОМ JSON ---

def load_data():
    """Завантажує дані з JSON файлу."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Помилка читання файлу: {e}")
            return {}
    return {}

def save_data(data):
    """Зберігає дані у JSON файл."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Помилка збереження файлу: {e}")

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://mcars-finance-bot-t3na.onrender.com")
    
    bot.reply_to(
        message, 
        f"Привіт! Твій ID: `{user_id}`\n\n"
        f"Твоє посилання для додатка на ПК:\n"
        f"{render_url}/get_json/{user_id}",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = str(message.from_user.id)
    text = message.text
    
    data = load_data()
    
    if user_id not in data:
        data[user_id] = []
    
    # Додаємо нове повідомлення
    data[user_id].append({"message": text})
    save_data(data)
    
    bot.reply_to(message, f"Записано в базу: {text}")

# --- FLASK API ENDPOINTS ---

@app.route('/')
def home():
    return "Finance Bot & Web Service is Running Alive!"

@app.route('/get_json/<user_id>', methods=['GET'])
def get_json(user_id):
    data = load_data()
    user_records = data.get(str(user_id), [])
    return jsonify(user_records)

# --- RUNNER ---

def run_bot():
    print("Запуск Telegram бота...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Запускаємо бота в окремому потоці
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запуск Flask сервера
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
