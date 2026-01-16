import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import os

# --- НАСТРОЙКИ ---
TOKEN = "8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg"
ADMIN_ID = "1211366782"
VERSION = "1.1.0 (Database Mode)" # Меняй это число, чтобы видеть обновление
DB_FILE = "results.txt"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def load_results():
    """Загружает результаты из текстового файла в память"""
    results = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == 3:
                    results.append({"name": parts[0], "score": parts[1], "date": parts[2]})
    return results

def save_result_to_file(name, score, date):
    """Дописывает один новый результат в файл"""
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name}|{score}|{date}\n")

# Загружаем историю при старте
results_history = load_results()

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"🤖 Бот 'Кибер-Щит' запущен!\nВерсия: {VERSION}\nСтатус БД: OK ({len(results_history)} записей)"
    )

@bot.message_handler(commands=['stats'])
def show_stats(message):
    # Перезагружаем из файла, чтобы точно были актуальные данные
    current_history = load_results()
    if not current_history:
        bot.send_message(message.chat.id, "📊 База данных пока пуста.")
        return
    
    text = f"📊 <b>ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ (v{VERSION}):</b>\n\n"
    # Показываем последние 10 записей
    for res in current_history[-10:]:
        text += f"👤 {res['name']}: <b>{res['score']}/20</b> ({res['date']})\n"
    bot.send_message(message.chat.id, text, parse_mode='html')

# --- API ДЛЯ САЙТА ---
@app.route('/send_result', methods=['POST'])
def receive_result():
    try:
        data = request.json
        name = data.get('name', 'Аноним')
        score = data.get('score', 0)
        time_now = datetime.now().strftime("%d.%m %H:%M")

        # 1. Сохраняем в файл (БАЗА ДАННЫХ)
        save_result_to_file(name, score, time_now)
        
        # 2. Обновляем в текущей памяти (для быстроты)
        results_history.append({"name": name, "score": score, "date": time_now})

        # 3. Уведомление в Telegram
        bot.send_message(ADMIN_ID, f"🛡 <b>НОВЫЙ РЕЗУЛЬТАТ!</b>\n👤 Имя: {name}\n✅ Баллы: {score}/20", parse_mode='html')
        
        print(f"Успешно сохранено: {name}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Ошибка сервера: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ЗАПУСК ---
def run_bot():
    print(f"Запуск бота версии {VERSION}...")
    bot.remove_webhook() # Сброс конфликтов
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Запуск бота в отдельном потоке
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Запуск Flask на порту Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
