import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import os
from collections import Counter # Специальный инструмент для подсчета ошибок

# --- НАСТРОЙКИ ---
TOKEN = "8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg"
ADMIN_ID = 1211366782  
VERSION = "1.4.0 (Error Analytics)"
DB_FILE = "results.txt"
ERRORS_FILE = "errors_log.txt" # Новый файл для хранения номеров вопросов
START_TIME = datetime.now()

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

def save_errors(wrong_questions):
    """Записывает номера ошибочных вопросов в отдельный лог"""
    if not wrong_questions: return
    with open(ERRORS_FILE, "a", encoding="utf-8") as f:
        # Сохраняем как одну строку через запятую
        line = ",".join(map(str, wrong_questions))
        f.write(line + "\n")

def get_top_errors_report():
    """Считает статистику ошибок и формирует текст"""
    if not os.path.exists(ERRORS_FILE):
        return "📈 Данных об ошибках пока нет."
    
    all_errors = []
    total_tests_with_errors = 0
    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            nums = line.strip().split(",")
            all_errors.extend(nums)
            total_tests_with_errors += 1
    
    if not all_errors: return "📈 Ошибок пока не зафиксировано."
    
    # Считаем частоту каждого номера вопроса
    counts = Counter(all_errors)
    # Берем 5 самых частых
    top_5 = counts.most_common(5)
    
    report = "⚠️ <b>АНАЛИТИКА ТРУДНЫХ ВОПРОСОВ:</b>\n\n"
    for q_id, count in top_5:
        report += f"❓ Вопрос №{q_id}: <b>{count}</b> ошибок\n"
    
    report += f"\n<i>Всего тестов с ошибками: {total_tests_with_errors}</i>"
    return report

# --- КЛАВИАТУРА ---
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stats = telebot.types.KeyboardButton("📊 Статистика")
    btn_status = telebot.types.KeyboardButton("🕒 Статус сервера")
    markup.add(btn_stats, btn_status)
    return markup

def is_admin(message):
    return message.from_user.id == ADMIN_ID

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Доступ закрыт.")
        return
    bot.send_message(message.chat.id, f"🤖 Система 'Кибер-Щит' активна.\nВерсия: {VERSION}", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_stats(message):
    if not is_admin(message): return

    # 1. Список последних результатов
    history = load_results()
    if not history:
        bot.send_message(message.chat.id, "📊 База данных пуста.")
        return
    
    text = f"📊 <b>ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ:</b>\n\n"
    for res in history[-10:]:
        text += f"👤 {res['name']}: <b>{res['score']}/20</b>\n"
    
    bot.send_message(message.chat.id, text, parse_mode='html')
    
    # 2. Аналитика ошибок (Топ-5)
    error_report = get_top_errors_report()
    bot.send_message(message.chat.id, error_report, parse_mode='html')

@bot.message_handler(func=lambda message: message.text == "🕒 Статус сервера")
def server_status(message):
    if not is_admin(message): return
    uptime = str(datetime.now() - START_TIME).split('.')[0]
    history = load_results()
    status_text = (
        f"🖥 <b>СТАТУС:</b>\n"
        f"✅ Аптайм: <code>{uptime}</code>\n"
        f"📁 Всего тестов: <b>{len(history)}</b>\n"
        f"🚀 Версия: {VERSION}"
    )
    bot.send_message(message.chat.id, status_text, parse_mode='html')

# --- API ДЛЯ САЙТА ---
@app.route('/send_result', methods=['POST', 'GET'])
def receive_result():
    # Если стучится Cron-job методом GET
    if request.method == 'GET':
        return "OK", 200

    try:
        data = request.json
        name = data.get('name', 'Аноним')
        score = data.get('score', 0)
        wrong_qs = data.get('wrong_questions', []) # Получаем список ошибок с сайта
        
        time_now = datetime.now().strftime("%d.%m %H:%M")

        # Сохраняем всё в файлы
        save_result_to_file(name, score, time_now)
        save_errors(wrong_qs)

        # Уведомление в Telegram
        msg = f"🛡 <b>НОВЫЙ РЕЗУЛЬТАТ!</b>\n👤 Имя: {name}\n✅ Баллы: {score}/20"
        if wrong_qs:
            msg += f"\n❌ Ошибки в вопросах: {', '.join(map(str, wrong_qs))}"
        
        bot.send_message(ADMIN_ID, msg, parse_mode='html')
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ЗАПУСК ---
def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

