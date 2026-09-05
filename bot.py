import os
import json
import threading
from flask import Flask, jsonify, request
import telebot
from telebot import types

# 1. Налаштування токена та ключа доступу
BOT_TOKEN = os.environ.get('BOT_TOKEN')
API_KEY = os.environ.get('API_KEY', 'my_secret_pc_key_123') # Ключ доступу для ПК

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

# --- СТРУКТУРА КАТЕГОРІЙ ТА ПІДКАТЕГОРІЙ ---
CATEGORIES = {
    "🚗 Транспорт": ["⛽ Пальне", "🛠 Ремонт", "🅿️ Парковка", "🚖 Таксі"],
    "🍔 Харчування": ["🛒 Продукти", "🍕 Ресторани / Кафе", "☕ Кава"],
    "🏠 Дом / Побут": ["🧾 Комунальні", "🧹 Товари для дому"],
    "🎮 Розваги": ["Игри", "🎬 Кіно", "🎧 Підписки"]
}

# Тимчасовий стан користувача для збереження обраної категорії
user_states = {}

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

# --- ІНЛАЙН-КНОПКИ (ПІД ПОВІДОМЛЕННЯМ) ---

def get_main_inline_keyboard():
    """Головне меню інлайн-кнопок"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Додати витрату", callback_data="add_expense"))
    markup.add(types.InlineKeyboardButton("📁 Отримати JSON", callback_data="get_json_file"))
    markup.add(types.InlineKeyboardButton("🔗 Посилання для ПК", callback_data="get_pc_link"))
    return markup

def get_categories_inline_keyboard():
    """Головні категорії витрат"""
    markup = types.InlineKeyboardMarkup()
    for cat in CATEGORIES.keys():
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"cat:{cat}"))
    markup.add(types.InlineKeyboardButton("❌ Скасувати", callback_data="cancel"))
    return markup

def get_subcategories_inline_keyboard(main_cat):
    """Підкатегорії + кнопка Назад"""
    markup = types.InlineKeyboardMarkup()
    subcats = CATEGORIES.get(main_cat, [])
    for sub in subcats:
        markup.add(types.InlineKeyboardButton(sub, callback_data=f"sub:{sub}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main_cat"))
    return markup

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    text = f"Привіт! Твій ID: `{user_id}`\n\nОбери дію з меню нижче:"
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_main_inline_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://mcars-finance-bot-t3na.onrender.com")

    if call.data == "add_expense":
        bot.edit_message_text("Обери головну категорію витрат:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_categories_inline_keyboard())

    elif call.data.startswith("cat:"):
        main_cat = call.data.split("cat:")[1]
        user_states[user_id] = {"main_cat": main_cat}
        bot.edit_message_text(f"Категорія: *{main_cat}*\nТепер обери підкатегорію:", chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_subcategories_inline_keyboard(main_cat))

    elif call.data == "back_to_main_cat":
        bot.edit_message_text("Обери головну категорію витрат:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_categories_inline_keyboard())

    elif call.data.startswith("sub:"):
        sub_cat = call.data.split("sub:")[1]
        main_cat = user_states.get(user_id, {}).get("main_cat", "Інше")
        user_states[user_id] = {"main_cat": main_cat, "sub_cat": sub_cat, "waiting_for_amount": True}
        bot.edit_message_text(f"Обрано: *{main_cat} -> {sub_cat}*\n\nВведи суму або опис витрати в чат:", chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown")

    elif call.data == "get_json_file":
        data = load_data()
        user_records = data.get(user_id, [])
        filename = f"{user_id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(user_records, f, ensure_ascii=False, indent=4)
        with open(filename, "rb") as doc:
            bot.send_document(chat_id, doc, caption="Ваші збережені дані JSON.")
        if os.path.exists(filename):
            os.remove(filename)

    elif call.data == "get_pc_link":
        text = f"Посилання для додатка ПК:\n`{render_url}/get_json/{user_id}?api_key={API_KEY}`"
        bot.send_message(chat_id, text, parse_mode="Markdown")

    elif call.data == "cancel":
        user_states.pop(user_id, None)
        bot.edit_message_text("Дію скасовано.", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_main_inline_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    user_id = str(message.from_user.id)
    text = message.text
    state = user_states.get(user_id, {})

    data = load_data()
    if user_id not in data:
        data[user_id] = []

    if state.get("waiting_for_amount"):
        record = {
            "main_category": state.get("main_cat"),
            "subcategory": state.get("sub_cat"),
            "value": text
        }
        data[user_id].append(record)
        save_data(data)
        user_states.pop(user_id, None)
        
        bot.reply_to(message, f"✅ Записано: {record['main_category']} -> {record['subcategory']}: {text}", reply_markup=get_main_inline_keyboard())
    else:
        # Звичайний запис
        data[user_id].append({"message": text})
        save_data(data)
        bot.reply_to(message, f"Записано в базу: {text}", reply_markup=get_main_inline_keyboard())

# --- FLASK API С ЗАХИСТОМ КЛЮЧЕМ API ---

@app.route('/')
def home():
    return "Finance Bot & Web Service is Running Alive!"

@app.route('/get_json/<user_id>', methods=['GET'])
def get_json(user_id):
    # Перевірка ключа через Header (X-API-Key) або URL параметр (?api_key=...)
    provided_key = request.headers.get("X-API-Key") or request.args.get("api_key")
    
    if provided_key != API_KEY:
        return jsonify({"error": "Unauthorized: Invalid API Key"}), 401
        
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
