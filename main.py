import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import os
import time

# --- НАСТРОЙКИ ---
TOKEN = "8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg"
ADMIN_ID = 1211366782  # Твой ID (как число)
VERSION = "1.2.0 (Security & Buttons)"
DB_FILE = "results.txt"
START_TIME = datetime.now() # Для отслеживания аптайма

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def load_results():
    results = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == 3:
                    results.append({"name": parts[0], "score": parts[1], "date": parts[2]})
    return results

def save_result_to_file(name, score, date):
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name}|{score}|{date}\n")

# --- КЛАВИАТУРА ---
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = telebot.types.KeyboardButton("📊 Статистика")
    btn_status = telebot.types.KeyboardButton("🕒 Статус сервера")
    markup.add(btn_stats, btn_status)
    return markup

# --- ПРОВЕРКА ДОСТУПА ---
def is_admin(message):
    return message.from_user.id == ADMIN_ID

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Доступ закрыт. Это приватный бот системы 'Кибер-Щит'.")
        return
    
    bot.send_message(
        message.chat.id, 
        f"🤖 Бот 'Кибер-Щит' запущен!\nВерсия: {VERSION}\n\nИспользуйте кнопки внизу для управления.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📊 Статистика" or message.text == "/stats")
def show_stats(message):
    if not is_admin(message): return

    history = load_results()
    if not history:
        bot.send_message(message.chat.id, "📊 База данных пока пуста.")
        return
    
    text = f"📊 <b>ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ (v{VERSION}):</b>\n\n"
    for res in history[-10:]:
        text += f"👤 {res['name']}: <b>{res['score']}/20</b> ({res['date']})\n"
    bot.send_message(message.chat.id, text, parse_mode='html')

@bot.message_handler(func=lambda message: message.text == "🕒 Статус сервера")
def server_status(message):
    if not is_admin(message): return
    
    uptime = datetime.now() - START_TIME
    # Отрезаем микросекунды для красоты
    uptime_str = str(uptime).split('.')[0]
    
    history = load_results()
    status_text = (
        f"🖥 <b>СТАТУС СЕРВЕРА:</b>\n\n"
        f"✅ Работает без перезагрузки: <code>{uptime_str}</code>\n"
        f"📁 Записей в базе: <b>{len(history)}</b>\n"
        f"🚀 Версия: {VERSION}"
    )
    bot.send_message(message.chat.id, status_text, parse_mode='html')

# --- API ДЛЯ САЙТА ---
@app.route('/send_result', methods=['POST'])
def receive_result():
    try:
        data = request.json
        name = data.get('name', 'Аноним')
        score = data.get('score', 0)
        time_now = datetime.now().strftime("%d.%m %H:%M")

        save_result_to_file(name, score, time_now)

        # Уведомление летит ТОЛЬКО админу по ADMIN_ID
        bot.send_message(ADMIN_ID, f"🛡 <b>НОВЫЙ РЕЗУЛЬТАТ!</b>\n👤 Имя: {name}\n✅ Баллы: {score}/20", parse_mode='html')
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Ошибка API: {e}")
        return jsonify({"status": "error"}), 500

# --- ЗАПУСК ---
def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
