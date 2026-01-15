import telebot
from telebot import types
from flask import Flask, request
import threading

# --- НАСТРОЙКИ (ЗАПОЛНИ СВОИМИ ДАННЫМИ) ---
TOKEN = '8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg'
MY_PASSWORD = '120110Lox' # Придумай свой пароль

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
auth_users = set() # Список тех, кто ввел пароль

# Сохранение в историю
def add_to_history(name, score):
    with open("history.txt", "a", encoding="utf-8") as f:
        f.write(f"👤 {name} — Результат: {score}/20\n")

# Прием данных с сайта
@app.route('/send_result', methods=['POST'])
def get_data():
    data = request.json
    add_to_history(data['name'], data['score'])
    return "OK", 200

# Кнопка меню
def get_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(types.KeyboardButton("📜 История"))
    return m

@bot.message_handler(commands=['start'])
def start(m):
    auth_users.discard(m.chat.id) # Сбрасываем вход при перезапуске
    bot.send_message(m.chat.id, "🔐 Введите пароль для доступа к админ-панели:")

@bot.message_handler(func=lambda m: m.chat.id not in auth_users)
def check_pass(m):
    if m.text == MY_PASSWORD:
        auth_users.add(m.chat.id)
        bot.send_message(m.chat.id, "✅ Доступ разрешен!", reply_markup=get_menu())
    else:
        bot.send_message(m.chat.id, "❌ Неверно. Введите пароль:")

@bot.message_handler(func=lambda m: m.text == "📜 История")
def show_hist(m):
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            text = f.read()
            bot.send_message(m.chat.id, text if text else "История пуста")
    except:
        bot.send_message(m.chat.id, "История пока пуста")

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)
