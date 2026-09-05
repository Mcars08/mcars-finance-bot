import json
import os
import random
import threading
from flask import Flask, jsonify
import requests
import telebot
from telebot import types

# ---------------------------------------------------------
# НАЛАШТУВАННЯ ХМАРНОЇ БАЗИ ДАНИХ ТА ТОКЕНА
# ---------------------------------------------------------
FIREBASE_URL = "https://mcarsfinance-a6624-default-rtdb.firebaseio.com/"
TOKEN = os.environ.get(
    'BOT_TOKEN', '8996181218:AAELaCNDCti2hWlr0sFeSuZbZmLeLHCbfP4'
)

# 1. Міні-сервер для Render (щоб тримати порт відкритим)
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive and connected to Firebase!'


@app.route('/get_json/<user_id>')
def get_user_json(user_id):
  """Отримує дані з хмари Firebase для конкретного користувача"""
  try:
    res = requests.get(
        f'{FIREBASE_URL}finance_data/{user_id}.json', timeout=5
    )
    if res.status_code == 200 and res.json():
      return jsonify(res.json())
    return jsonify([])
  except Exception as e:
    return jsonify([])


def run():
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = threading.Thread(target=run, daemon=True)
  t.start()


keep_alive()

# 2. Ініціалізація Telegram-бота
bot = telebot.TeleBot(TOKEN)

# Словник для збереження стану користувача
user_state = {}


# Функції для роботи з Firebase Realtime Database замість локальних файлів
def load_firebase_data(path='finance_data'):
  try:
    res = requests.get(f'{FIREBASE_URL}{path}.json', timeout=5)
    if res.status_code == 200 and res.json():
      return res.json()
    return {}
  except Exception as e:
    print(f'Помилка завантаження з Firebase: {e}')
    return {}


def save_firebase_data(path, data):
  try:
    res = requests.put(f'{FIREBASE_URL}{path}.json', json=data, timeout=5)
    return res.status_code == 200
  except Exception as e:
    print(f'Помилка збереження у Firebase: {e}')
    return False


# Головне меню
def get_main_markup():
  markup = types.InlineKeyboardMarkup(row_width=1)
  btn1 = types.InlineKeyboardButton(
      '🔑 Отримати код авторизації для ПК', callback_data='btn_key'
  )
  btn2 = types.InlineKeyboardButton(
      '➕ Додати транзакцію', callback_data='btn_add'
  )
  btn3 = types.InlineKeyboardButton(
      '📊 Переглянути прибуток', callback_data='btn_profit'
  )
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
      '🏎️ MCARS & FINANCE CONTROL BOT (CLOUD EDITION)\n\nОберіть дію:',
      reply_markup=get_main_markup(),
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
        text='🏎️ MCARS & FINANCE CONTROL BOT (CLOUD EDITION)\n\nОберіть дію:',
        reply_markup=get_main_markup(),
    )

  elif call.data == 'btn_key':
    code = random.randint(100000, 999999)

    # Збереження коду у хмару Firebase
    keys_data = load_firebase_data('user_keys')
    keys_data[user_id] = code
    save_firebase_data('user_keys', keys_data)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            '🔙 Головне меню', callback_data='main_menu'
        )
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            f'🔑 Ваш код для входу в програму на ПК:'
            f' <code>{code}</code>\n\nВведіть цей код у вікні програми при'
            ' першому запуску.'
        ),
        parse_mode='HTML',
        reply_markup=markup,
    )

  elif call.data == 'btn_add':
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            '🚗 Машина', callback_data='group_Машина'
        ),
        types.InlineKeyboardButton('🪙 Крипта', callback_data='group_Крипта'),
        types.InlineKeyboardButton('💼 Бізнес', callback_data='group_Бізнес'),
        types.InlineKeyboardButton('🛒 Покупки', callback_data='group_Покупки'),
    )
    markup.add(
        types.InlineKeyboardButton(
            '✈️ Подорожі', callback_data='group_Подорожі'
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            '🔙 Головне меню', callback_data='main_menu'
        )
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='📂 Оберіть головну групу:',
        reply_markup=markup,
    )

  elif call.data.startswith('group_'):
    group_name = call.data.split('_')[1]
    user_state[user_id] = {'group': group_name}

    markup = types.InlineKeyboardMarkup(row_width=2)
    if group_name == 'Машина':
      markup.add(
          types.InlineKeyboardButton(
              '🛠️ Ремонт', callback_data='sub_Ремонт'
          ),
          types.InlineKeyboardButton('⛽ Пальне', callback_data='sub_Пальне'),
          types.InlineKeyboardButton(
              '📋 Загальне', callback_data='sub_Загальне'
          ),
      )
    elif group_name == 'Крипта':
      markup.add(
          types.InlineKeyboardButton('📈 Покупка', callback_data='sub_Покупка'),
          types.InlineKeyboardButton('📉 Продаж', callback_data='sub_Продаж'),
      )
    elif group_name == 'Бізнес':
      markup.add(
          types.InlineKeyboardButton('📥 Доходи', callback_data='sub_Доходи'),
          types.InlineKeyboardButton('📤 Витрати', callback_data='sub_Витрати'),
      )
    else:
      markup.add(
          types.InlineKeyboardButton(
              '📋 Загальне', callback_data='sub_Загальне'
          )
      )

    markup.add(
        types.InlineKeyboardButton(
            '🔙 Назад до груп', callback_data='btn_add'
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            '🔙 Головне меню', callback_data='main_menu'
        )
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f'📁 Група: {group_name}\nОберіть підгрупу:',
        reply_markup=markup,
    )

  elif call.data.startswith('sub_'):
    sub_name = call.data.split('_')[1]
    if user_id in user_state:
      user_state[user_id]['subgroup'] = sub_name
      user_state[user_id]['step'] = 'waiting_amount'

    group = user_state[user_id]['group']

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            '🔙 Головне меню', callback_data='main_menu'
        )
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            f'📂 {group} -> {sub_name}\n\n✍️ Введіть суму та опис (наприклад:'
            ' <code>1500 Дохід</code> або <code>-500 Витрата</code>):'
        ),
        parse_mode='HTML',
        reply_markup=markup,
    )

  elif call.data == 'btn_profit':
    # Завантаження даних користувача з Firebase
    user_records = load_firebase_data(f'finance_data/{user_id}')

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            '🔙 Головне меню', callback_data='main_menu'
        )
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            '📊 Ваші збережені дані в хмарі Firebase:\n'
            f'<code>{json.dumps(user_records, ensure_ascii=False, indent=2)}</code>'
        ),
        parse_mode='HTML',
        reply_markup=markup,
    )


# 5. Обробка введення суми транзакції
@bot.message_handler(func=lambda message: True)
def handle_text(message):
  user_id = str(message.chat.id)

  if (
      user_id in user_state
      and user_state[user_id].get('step') == 'waiting_amount'
  ):
    data = user_state[user_id]
    group = data['group']
    subgroup = data['subgroup']

    parts = message.text.split(' ', 1)
    try:
      amount = float(parts[0].replace(',', '.'))
      description = parts[1] if len(parts) > 1 else 'Загальне'

      trans_type = 'income' if amount >= 0 else 'expense'

      # 1. Завантажуємо поточний список транзакцій користувача
      trans_list = load_firebase_data(f'finance_data/{user_id}')
      if not isinstance(trans_list, list):
        trans_list = []

      # 2. Формуємо об'єкт запису
      new_trans = {
          'cat': group,
          'sub': subgroup,
          'amount': abs(amount),
          'type': trans_type,
          'details': description,
          'currency': 'грн',
          'timestamp': (
              message.date
          ),  # Зберігаємо точний час надсилання повідомлення
      }

      trans_list.append(new_trans)

      # 3. Відправляємо оновлені дані у Firebase Realtime Database
      save_firebase_data(f'finance_data/{user_id}', trans_list)

      sign_str = f'+{amount:.2f}' if amount >= 0 else f'{amount:.2f}'

      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton('➕ Додати ще', callback_data='btn_add')
      )
      markup.add(
          types.InlineKeyboardButton(
              '🔙 Головне меню', callback_data='main_menu'
          )
      )

      bot.send_message(
          message.chat.id,
          f'✅ Успішно збережено в хмару!\n\n📂 {group} -> {subgroup}'
          f' ({description})\n📝 Сума: {sign_str} грн',
          reply_markup=markup,
      )
      del user_state[user_id]

    except ValueError:
      bot.send_message(
          message.chat.id,
          '⚠️ Будь ласка, введіть суму коректно (наприклад: <code>1500'
          ' Дохід</code> або <code>-500 Витрата</code>)',
          parse_mode='HTML',
      )
  else:
    bot.send_message(
        message.chat.id, '⚠️ Натисніть /start, щоб відкрити меню з кнопками.'
    )


if __name__ == '__main__':
  print('Запуск Telegram бота та вебсерверу...')
  try:
    bot.remove_webhook()
  except Exception as e:
    print(f'Видалення вебхуку: {e}')
  bot.infinity_polling()
