import json
import os
import random
import time
import telebot
from telebot import types

TOKEN = "8996181218:AAG1HEmDv6JKM6Ibp81k1798B5NmzU15DNE"
bot = telebot.TeleBot(TOKEN)

user_states = {}
KEYS_FILE = "user_keys.json"


def get_user_file(user_id):
  return f"finance_data_{user_id}.json"


def load_keys():
  if os.path.exists(KEYS_FILE):
    try:
      with open(KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {}


def save_keys(keys):
  with open(KEYS_FILE, "w", encoding="utf-8") as f:
    json.dump(keys, f, ensure_ascii=False, indent=4)


def load_data(user_id):
  filename = get_user_file(user_id)
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {
      "transactions": [],
      "categories": ["Машина", "Бізнес", "Крипта", "Покупки", "Подорожі"],
      "submenus": {
          "Машина": [],
          "Бізнес": [],
          "Крипта": [],
          "Покупки": [],
          "Подорожі": [],
      },
      "images": {},
      "goals": [],
  }


def save_data(user_id, data):
  filename = get_user_file(user_id)
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


@bot.message_handler(commands=["start", "menu"])
def send_welcome(message):
  markup = types.InlineKeyboardMarkup(row_width=1)
  btn_auth = types.InlineKeyboardButton(
      "🔑 Отримати код авторизації для ПК", callback_data="get_auth_code"
  )
  btn_add = types.InlineKeyboardButton(
      "➕ Додати транзакцію", callback_data="btn_add"
  )
  btn_balance = types.InlineKeyboardButton(
      "📊 Переглянути прибуток", callback_data="btn_balance"
  )
  markup.add(btn_auth, btn_add, btn_balance)

  bot.send_message(
      message.chat.id,
      "🏎️ **MCARS & FINANCE CONTROL BOT**\n\nОберіть дію:",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
  chat_id = call.message.chat.id
  user_id = call.from_user.id

  if call.data == "get_auth_code":
    # Генерація 6-значного одноразового коду
    code = str(random.randint(100000, 999999))
    keys = load_keys()
    keys[code] = user_id
    save_keys(keys)

    bot.send_message(
      chat_id,
      f"🔑 Ваш код для входу в програму на ПК: `{code}`\n\n"
      "Введіть цей код у вікні програми при першому запуску.",
      parse_mode="Markdown",
    )

  elif call.data == "btn_add":
    data = load_data(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    categories = data.get(
        "categories", ["Машина", "Бізнес", "Крипта", "Покупки", "Подорожі"]
    )
    buttons = [
        types.InlineKeyboardButton(cat, callback_data=f"cat_{cat}")
        for cat in categories
    ]
    markup.add(*buttons)

    bot.edit_message_text(
        "Оберіть категорію:",
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
    )

  elif call.data.startswith("cat_"):
    cat_name = call.data.split("cat_")[1]
    user_states[user_id] = {"cat": cat_name}

    data = load_data(user_id)
    submenus = data.get("submenus", {}).get(cat_name, [])
    if not submenus:
      submenus = ["Загальне"]

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(sub, callback_data=f"sub_{sub}")
        for sub in submenus
    ]
    markup.add(*buttons)

    bot.edit_message_text(
        f"Категорія: **{cat_name}**\nОберіть об'єкт/менюшку:",
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )

  elif call.data.startswith("sub_"):
    sub_name = call.data.split("sub_")[1]
    if user_id not in user_states:
      user_states[user_id] = {}
    user_states[user_id]["sub"] = sub_name

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_inc = types.InlineKeyboardButton(
        "⊕ Дохід (+)", callback_data="type_income"
    )
    btn_exp = types.InlineKeyboardButton(
        "⊖ Витрата (-)", callback_data="type_expense"
    )
    markup.add(btn_inc, btn_exp)

    bot.edit_message_text(
        f"Менюшка: **{sub_name}**\nОберіть тип операції:",
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown",
    )

  elif call.data in ["type_income", "type_expense"]:
    trans_type = "income" if call.data == "type_income" else "expense"
    if user_id not in user_states:
      user_states[user_id] = {}
    user_states[user_id]["type"] = trans_type

    msg = bot.send_message(
        chat_id,
        "✍️ **Введіть суму та опис через пробіл**\nНаприклад: `1500 Купівля"
        " деталей` або просто `500`:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_amount_and_details)

  elif call.data == "btn_balance":
    data = load_data(user_id)
    trans = data.get("transactions", [])
    inc = sum(t["amount"] for t in trans if t.get("type") == "income")
    exp = sum(t["amount"] for t in trans if t.get("type") == "expense")
    bal = inc - exp

    bot.send_message(
        chat_id,
        f"📊 **ВАШ ОСОБИСТИЙ БАЛАНС:**\n\n🟢 Доходи: {inc:.2f} грн\n🔴 Витрати:"
        f" {exp:.2f} грн\n💰 Чистий прибуток: **{bal:.2f} грн**",
        parse_mode="Markdown",
    )


def process_amount_and_details(message):
  chat_id = message.chat.id
  user_id = message.from_user.id
  text = message.text.strip()

  try:
    parts = text.split(" ", 1)
    amount = float(parts[0].replace(",", "."))
    details = parts[1] if len(parts) > 1 else "Додано з Telegram"

    st = user_states.get(user_id, {})
    cat = st.get("cat", "Машина")
    sub = st.get("sub", "Загальне")
    t_type = st.get("type", "expense")

    data = load_data(user_id)
    data["transactions"].append({
        "timestamp": time.time(),
        "type": t_type,
        "cat": cat,
        "sub": sub,
        "details": details,
        "amount": amount,
        "currency": "грн",
    })
    save_data(user_id, data)

    sign = "+" if t_type == "income" else "-"
    bot.send_message(
        chat_id,
        f"✅ **Успішно збережено!**\n\n📂 [{cat} -> {sub}]\n📝 {details}:"
        f" **{sign}{amount:.2f} грн**",
        parse_mode="Markdown",
    )
  except Exception:
    msg = bot.send_message(
        chat_id,
        "❌ **Помилка!** Будь ласка, вкажіть суму числом.",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_amount_and_details)


print("🤖 Авторизаційний Telegram-бот запущено!")
bot.polling(none_stop=True)
