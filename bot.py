import os
import json
import threading
from flask import Flask, jsonify, request
import telebot
from telebot import types

# 1. Налаштування токена та ключа доступу
BOT_TOKEN = os.environ.get('BOT_TOKEN')
API_KEY = os.environ.get('API_KEY', '448314') # Ключ для програми на ПК

if not BOT_TOKEN:
    raise ValueError("Помилка: BOT_TOKEN не знайдено у змінних оточення Render!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

# Тимчасовий стан для операцій користувача
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

# --- ІНЛАЙН-МЕНЮ ---

def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔑 Отримати код авторизації для ПК", callback_data="get_code"),
        types.InlineKeyboardButton("➕ Додати транзакцію", callback_data="add_transaction"),
        types.InlineKeyboardButton("📊 Переглянути прибуток", callback_data="view_profit")
    )
    return markup

def get_main_categories_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏢 Бізнес", callback_data="main_cat:Бізнес"),
        types.InlineKeyboardButton("🚗 Машини", callback_data="main_cat:Машини"),
        types.InlineKeyboardButton("🏠 Головне меню", callback_data="back_to_main")
    )
    return markup

def get_subcategories_menu(main_category):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if main_category == "Бізнес":
        markup.add(
            types.InlineKeyboardButton("🛒 Магазин", callback_data="sub_cat:Магазин"),
            types.InlineKeyboardButton("⛽ АЗС", callback_data="sub_cat:АЗС"),
            types.InlineKeyboardButton("🏢 Нафтовишка", callback_data="sub_cat:Нафтовишка"),
            types.InlineKeyboardButton("📋 Інше", callback_data="sub_cat:Інше бізнес")
        )
    elif main_category == "Машини":
        markup.add(
            types.InlineKeyboardButton("🏎️ Спортивні", callback_data="sub_cat:Спортивні"),
            types.InlineKeyboardButton("🚚 Вантажні", callback_data="sub_cat:Вантажні"),
            types.InlineKeyboardButton("🚙 Позашляховики", callback_data="sub_cat:Позашляховики"),
            types.InlineKeyboardButton("📋 Загальне", callback_data="sub_cat:Загальне машина")
        )
    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="add_transaction"),
        types.InlineKeyboardButton("🏠 Головне меню", callback_data="back_to_main")
    )
    return markup

def get_transaction_type_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🟢 Дохід (+)", callback_data="type:income"),
        types.InlineKeyboardButton("🔴 Витрата (-)", callback_data="type:expense")
    )
    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_categories"),
        types.InlineKeyboardButton("🏠 Головне меню", callback_data="back_to_main")
    )
    return markup

def get_back_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_type"),
        types.InlineKeyboardButton("🏠 Головне меню", callback_data="back_to_main")
    )
    return markup

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    text = "🚗 *MCARS & FINANCE CONTROL BOT*\n\nОберіть дію:"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = str(call.from_user.id)
    chat_id = call.message.chat.id
    
    if call.data == "get_code":
        code = API_KEY
        text = f"🔑 Ваш код для входу в програму на ПК: `{code}`\n\nВведіть цей код у вікні програми при першому запуску."
        bot.send_message(chat_id, text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "add_transaction":
        text = "📁 *Оберіть розділ:*"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_main_categories_menu())

    elif call.data.startswith("main_cat:"):
        main_cat = call.data.split("main_cat:")[1]
        user_states[user_id] = {"main_cat": main_cat}
        text = f"📂 Розділ: *{main_cat}*\nОберіть категорію:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_subcategories_menu(main_cat))

    elif call.data.startswith("sub_cat:"):
        sub_cat = call.data.split("sub_cat:")[1]
        if user_id in user_states:
            user_states[user_id]["sub_cat"] = sub_cat
        text = f"⚙️ Обрано: *{sub_cat}*\nОберіть тип операції:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_transaction_type_menu())

    elif call.data.startswith("type:"):
        t_type = call.data.split("type:")[1]
        if user_id in user_states:
            user_states[user_id]["action"] = "wait_for_transaction"
            user_states[user_id]["trans_type"] = t_type
        
        type_name = "Дохід (+)" if t_type == "income" else "Витрата (-)"
        state = user_states.get(user_id, {})
        text = f"📝 *{state.get('main_cat')} -> {state.get('sub_cat')}* ({type_name})\n\nВведіть суму та опис через пробіл.\nНаприклад: `1500 Купівля деталей` або просто `500`:"
        
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_back_menu())

    elif call.data == "back_to_categories":
        state = user_states.get(user_id, {})
        main_cat = state.get("main_cat", "Машини")
        text = f"📂 Розділ: *{main_cat}*\nОберіть категорію:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_subcategories_menu(main_cat))

    elif call.data == "back_to_type":
        text = "⚙️ Оберіть тип операції:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_transaction_type_menu())

    elif call.data == "view_profit":
        data = load_data()
        user_records = data.get(user_id, [])
        text = f"📊 Ваші збережені дані:\n`{json.dumps(user_records, ensure_ascii=False, indent=2)}`"
        bot.send_message(chat_id, text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "back_to_main":
        user_states.pop(user_id, None)
        text = "🚗 *MCARS & FINANCE CONTROL BOT*\n\nОберіть дію:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    user_id = str(message.from_user.id)
    text = message.text
    chat_id = message.chat.id
    
    state = user_states.get(user_id, {})
    
    if state.get("action") == "wait_for_transaction":
        t_type = state.get("trans_type")
        main_cat = state.get("main_cat")
        sub_cat = state.get("sub_cat")
        parts = text.split(maxsplit=1)
        
        try:
            amount_float = float(parts[0])
            if t_type == "expense":
                amount_float = -abs(amount_float)
            else:
                amount_float = abs(amount_float)
                
            description = parts[1] if len(parts) > 1 else "Без опису"
            
            data = load_data()
            if user_id not in data:
                data[user_id] = []
                
            record = {
                "main_category": main_cat,
                "subcategory": sub_cat,
                "amount": amount_float,
                "description": description
            }
            data[user_id].append(record)
            save_data(data)
            
            sign_str = f"+{amount_float}" if amount_float > 0 else str(amount_float)
            response_text = f"✅ Успішно збережено!\n\n📁 {main_cat} -> {sub_cat}\n📝 Додано з Telegram: {sign_str} грн ({description})"
            
            bot.send_message(chat_id, response_text, reply_markup=get_main_menu())
            user_states.pop(user_id, None)
            
        except ValueError:
            bot.reply_to(message, "⚠️ Помилка! Першим словом має бути число (сума). Спробуйте ще раз або скористайтеся кнопками.")
    else:
        bot.send_message(chat_id, "Будь ласка, скористайтеся кнопками меню або почніть з команди /start", reply_markup=get_main_menu())

# --- FLASK API ---

@app.route('/')
def home():
    return "Finance Bot & Web Service is Running Alive!"

@app.route('/get_json/<user_id>', methods=['GET'])
def get_json(user_id):
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
