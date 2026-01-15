import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading

# --- НАСТРОЙКИ ---
TOKEN = "8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg"
ADMIN_ID = "1211366782"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app) # Это РАЗРЕШАЕТ сайту слать данные на сервер

results_history = []

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 Бот системы 'Кибер-Щит' запущен!\nИспользуй /stats для просмотра результатов.")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not results_history:
        bot.send_message(message.chat.id, "Пока никто не прошел тест.")
        return
    
    text = "📊 <b>ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ:</b>\n\n"
    for res in results_history[-10:]: # Показать последние 10
        text += f"👤 {res['name']}: <b>{res['score']}/20</b> ({res['date']})\n"
    bot.send_message(message.chat.id, text, parse_mode='html')

# --- API ДЛЯ САЙТА ---
@app.route('/send_result', methods=['POST'])
def receive_result():
    data = request.json
    name = data.get('name', 'Аноним')
    score = data.get('score', 0)
    time_now = datetime.now().strftime("%H:%M:%S")

    # Сохраняем в память
    results_history.append({"name": name, "score": score, "date": time_now})

    # Отправляем мгновенное уведомление админу
    try:
        bot.send_message(ADMIN_ID, f"🛡 <b>НОВЫЙ РЕЗУЛЬТАТ!</b>\n👤 Имя: {name}\n✅ Баллы: {score}/20", parse_mode='html')
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}")

    return jsonify({"status": "success"}), 200

# Запуск бота в отдельном потоке, чтобы Flask работал параллельно
def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
