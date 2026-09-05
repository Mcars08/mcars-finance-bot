import json
import os
import random
import threading
from flask import Flask, jsonify
import telebot
from telebot import types

# 1. Міні-сервер для Render (щоб тримати порт відкритим та віддавати JSON на ПК)
app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

@app.route('/get_json/<user_id>')
def get_user_json(user_id):
    """Віддає дані у форматі JSON тільки для конкретного користувача за його ID"""
    if os.path.exists('finance_data.json'):
        with open('finance_data.json', 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                user_records = data.get(str(user_id), [])
                return jsonify(user_records)
            except:
                return jsonify([])
    return jsonify([])

def run():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()

keep_alive()

# 2. Токен бота (можна брати зі змінних оточення Render або вставити сюди)
TOKEN = os.environ.get('BOT_TOKEN', '8996181218:AAELaCNDCti2hWlr0sFeSuZbZmLeLHCbfP4')
bot = telebot.TeleBot(TOKEN)

# Словник для збереження стану користувача
user_state = {}

# Функції для роботи з JSON файлами
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Головне меню (винесено в окрему функцію для зручного повернення)
def get_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton('🔑 Отримати код авторизації для ПК', callback_data='btn_key')
    btn2 = types.InlineKeyboardButton('➕ Додати транзакцію', callback_data='btn_add')
    btn3 = types.InlineKeyboardButton('📊 Переглянути прибуток', callback_data='btn_profit')
    markup.add(btn1, btn2, btn3)
    return markup

# 3. Головне меню при команді /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.chat.id)
    if user_id in user_state:
        del user_state[user_id]

    bot.send_message(
        message.chat.id,
        '🚗 MCARS & FINANCE CONTROL BOT\n\nОберіть дію:',
        reply_markup=get_main_markup()
    )

# 4. Обробка всіх натискань на інлайн-кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = str(call.message.chat.id)

    if call.data == 'main_menu':
        if user_id in user_state:
            del user_state[user_id]
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='🚗 MCARS & FINANCE CONTROL BOT\n\nОберіть дію:',
            reply_markup=get_main_markup()
        )

    elif call.data == 'btn_key':
        code = random.randint(100000, 999999)
        keys_data = load_json('user_keys.json')
        keys_data[user_id] = code
        save_json('user_keys.json', keys_data)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f'🔑 Ваш код для входу в програму на ПК: <code>{code}</code>\n\nВведіть цей код у вікні програми при першому запуску.',
            parse_mode='HTML',
            reply_markup=markup
        )

    elif call.data == 'btn_add':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('🚗 Машина', callback_data='group_Машина'),
            types.InlineKeyboardButton('🪙 Крипта', callback_data='group_Крипта'),
            types.InlineKeyboardButton('💼 Бізнес', callback_data='group_Бізнес'),
            types.InlineKeyboardButton('🛒 Покупки', callback_data='group_Покупки')
        )
        markup.add(
            types.InlineKeyboardButton('✈️ Подорожі', callback_data='group_Подорожі')
        )
        markup.add(
            types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu')
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='📂 Оберіть головну групу:',
            reply_markup=markup
        )

    elif call.data.startswith('group_'):
        group_name = call.data.split('_')[1]
        user_state[user_id] = {'group': group_name}

        markup = types.InlineKeyboardMarkup(row_width=2)
        if group_name == 'Машина':
            markup.add(
                types.InlineKeyboardButton('🛠️ Ремонт', callback_data='sub_Ремонт'),
                types.InlineKeyboardButton('⛽ Пальне', callback_data='sub_Пальне'),
                types.InlineKeyboardButton('📋 Загальне', callback_data='sub_Загальне')
            )
        elif group_name == 'Крипта':
            markup.add(
                types.InlineKeyboardButton('📈 Покупка', callback_data='sub_Покупка'),
                types.InlineKeyboardButton('📉 Продаж', callback_data='sub_Продаж')
            )
        elif group_name == 'Бізнес':
            markup.add(
                types.InlineKeyboardButton('📥 Доходи', callback_data='sub_Доходи'),
                types.InlineKeyboardButton('📤 Витрати', callback_data='sub_Витрати')
            )
        else:
            markup.add(
                types.InlineKeyboardButton('📋 Загальне', callback_data='sub_Загальне')
            )
        
        markup.add(types.InlineKeyboardButton('🔙 Назад до груп', callback_data='btn_add'))
        markup.add(types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f'📁 Група: {group_name}\nОберіть підгрупу:',
            reply_markup=markup
        )

    elif call.data.startswith('sub_'):
        sub_name = call.data.split('_')[1]
        if user_id in user_state:
            user_state[user_id]['subgroup'] = sub_name
            user_state[user_id]['step'] = 'waiting_amount'

        group = user_state[user_id]['group']
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f'📂 {group} -> {sub_name}\n\n✍️ Введіть суму та опис (наприклад: <code>1500 Дохід</code> або <code>-500 Витрата</code>):',
            parse_mode='HTML',
            reply_markup=markup
        )

    elif call.data == 'btn_profit':
        finance_data = load_json('finance_data.json')
        user_records = finance_data.get(user_id, [])
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f'📊 Ваші збережені дані:\n<code>{json.dumps(user_records, ensure_ascii=False, indent=2)}</code>',
            parse_mode='HTML',
            reply_markup=markup
        )

# 5. Обробка введення суми транзакції
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = str(message.chat.id)

    if user_id in user_state and user_state[user_id].get('step') == 'waiting_amount':
        data = user_state[user_id]
        group = data['group']
        subgroup = data['subgroup']

        parts = message.text.split(' ', 1)
        try:
            amount = float(parts[0])
            description = parts[1] if len(parts) > 1 else 'Загальне'

            finance_data = load_json('finance_data.json')
            trans_list = finance_data.get(user_id, [])
            if not isinstance(trans_list, list):
                trans_list = []

            trans_list.append({
                'group': group,
                'subgroup': subgroup,
                'amount': amount,
                'description': description
            })
            finance_data[user_id] = trans_list
            save_json('finance_data.json', finance_data)

            sign_str = f'+{amount:.2f}' if amount >= 0 else f'{amount:.2f}'
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('➕ Додати ще', callback_data='btn_add'))
            markup.add(types.InlineKeyboardButton('🔙 Головне меню', callback_data='main_menu'))

            bot.send_message(
                message.chat.id,
                f'✅ Успішно збережено!\n\n📂 {group} -> {subgroup} ({description})\n📝 Сума: {sign_str} грн',
                reply_markup=markup
            )
            del user_state[user_id]
        except ValueError:
            bot.send_message(
                message.chat.id,
                '⚠️ Будь ласка, введіть суму коректно (наприклад: <code>1500 Дохід</code> або <code>-500 Витрата</code>)',
                parse_mode='HTML'
            )
    else:
        bot.send_message(
            message.chat.id,
            '⚠️ Натисніть /start, щоб відкрити меню з кнопками.'
        )

if __name__ == '__main__':
    print("Запуск Telegram бота та вебсерверу...")
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Видалення вебхуку: {e}")
    bot.infinity_polling()
