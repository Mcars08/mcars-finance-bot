import os
import json
import threading
from flask import Flask, jsonify, send_file
import telebot

BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Помилка читання файлу: {e}")
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Помилка збереження файлу: {e}")

def create_user_json_file(user_id, records):
    """Створює тимчасовий файлик USER_ID.json для надсилання в Telegram."""
    filename = f"{user_id}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    return filename

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://mcars-finance-bot-t3na.onrender.com")
    
    data = load_data()
    user_records = data.get(user_id, [])
    
    text = (
        f"Привіт! Твій ID: {user_id}\n\n"
        f"Твоє посилання для додатка на ПК:\n"
        f"{render_url}/get_json/{user_id}"
    )
    bot.reply_to(message, text)
    
    # Створюємо та відправляємо файл .json у чат
    filename = create_user_json_file(user_id, user_records)
    with open(filename, "rb") as doc:
        bot.send_document(message.chat.id, doc)
    
    if os.path.exists(filename):
        os.remove(filename)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = str(message.from_user.id)
    text = message.text
    
    data = load_data()
    if user_id not in data:
        data[user_id] = []
        
    # Додаємо запис
    data[user_id].append({"message": text})
    save_data(data)
    
    # Формуємо та надсилаємо оновлений файл .json
    filename = create_user_json_file(user_id, data[user_id])
    with open(filename, "rb") as doc:
        bot.send_document(
            message.chat.id, 
            doc, 
            caption=f"Записано в базу: {text}"
        )
        
    if os.path.exists(filename):
        os.remove(filename)

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

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print("Запуск Telegram бота...")
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Видалення вебхуку: {e}")
        
    bot.infinity_polling()
