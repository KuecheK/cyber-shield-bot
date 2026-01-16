import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import os
import json
from collections import Counter

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8547514667:AAETrqXRxnjyjeNecUZa-suEdeSbSjsnDbg")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1211366782"))
VERSION = "2.0.0 (Advanced Analytics)"
DB_FILE = "results.json"
ERRORS_FILE = "errors_log.json"
MESSAGES_FILE = "messages.json"
START_TIME = datetime.now()

# Состояние ввода сообщения
admin_waiting_for_message = False

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST"]}})

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def load_results():
    """Загружает результаты тестов из JSON"""
    results = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
        except:
            results = []
    return results

def save_result_to_file(name, score, date, suspicious_data=None):
    """Сохраняет результат теста в JSON"""
    results = load_results()
    result = {
        "name": name,
        "score": score,
        "date": date,
        "suspicious": suspicious_data or {}
    }
    results.append(result)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def load_messages():
    """Загружает сообщения из JSON"""
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_message(text):
    """Сохраняет новое сообщение"""
    messages = load_messages()
    messages.append({
        "text": text,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def clear_messages():
    """Очищает все сообщения"""
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def save_errors(wrong_questions):
    """Сохраняет вопросы с ошибками для аналитики"""
    if not wrong_questions:
        return
    
    errors_log = []
    if os.path.exists(ERRORS_FILE):
        try:
            with open(ERRORS_FILE, "r", encoding="utf-8") as f:
                errors_log = json.load(f)
        except:
            errors_log = []
    
    errors_log.append({
        "timestamp": datetime.now().strftime("%d.%m %H:%M:%S"),
        "questions": wrong_questions
    })
    
    with open(ERRORS_FILE, "w", encoding="utf-8") as f:
        json.dump(errors_log, f, ensure_ascii=False, indent=2)

def get_top_errors_report():
    """Считает статистику ошибок и формирует текст"""
    if not os.path.exists(ERRORS_FILE):
        return "📈 Данных об ошибках пока нет."
    
    all_errors = []
    total_tests_with_errors = 0
    
    try:
        with open(ERRORS_FILE, "r", encoding="utf-8") as f:
            errors_log = json.load(f)
            for entry in errors_log:
                all_errors.extend(entry.get("questions", []))
                total_tests_with_errors += 1
    except:
        return "📈 Ошибка при чтении логов."
    
    if not all_errors:
        return "📈 Ошибок пока не зафиксировано."
    
    counts = Counter(all_errors)
    top_10 = counts.most_common(10)
    
    report = "⚠️ <b>ТОП-10 ТРУДНЫХ ВОПРОСОВ:</b>\n\n"
    for idx, (q_id, count) in enumerate(top_10, 1):
        report += f"{idx}. Вопрос №{q_id}: <b>{count}</b> ошибок\n"
    
    report += f"\n<i>Всего тестов с ошибками: {total_tests_with_errors}</i>"
    return report

# --- КЛАВИАТУРА ---
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton("📊 Статистика"),
        telebot.types.KeyboardButton("🕒 Статус сервера"),
        telebot.types.KeyboardButton("⚠️ Трудные вопросы"),
        telebot.types.KeyboardButton("📢 Отправить сообщение"),
        telebot.types.KeyboardButton("🗑️ Очистить доску"),
    )
    return markup

def is_admin(message):
    return message.from_user.id == ADMIN_ID

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "❌ Доступ закрыт. Это админ-панель.")
        return
    welcome_text = (
        f"🤖 <b>КИБЕР-ЩИТ АДМИН-ПАНЕЛЬ</b>\n"
        f"Версия: {VERSION}\n\n"
        f"Статус: ✅ Активна"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='html', reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_stats(message):
    if not is_admin(message):
        return

    results = load_results()
    if not results:
        bot.send_message(message.chat.id, "📊 База данных пуста.")
        return
    
    recent = results[-10:]
    text = f"📊 <b>ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ (макс 10):</b>\n\n"
    for i, res in enumerate(recent, 1):
        score = res.get('score', 0)
        suspicious = res.get('suspicious', {})
        flag = "⚠️" if suspicious.get('is_suspicious') else "✅"
        text += f"{i}. {flag} {res['name']}: <b>{score}/17</b> | {res['date']}\n"
    
    bot.send_message(message.chat.id, text, parse_mode='html')

@bot.message_handler(func=lambda message: message.text == "🕒 Статус сервера")
def server_status(message):
    if not is_admin(message):
        return
    
    uptime = str(datetime.now() - START_TIME).split('.')[0]
    results = load_results()
    avg_score = sum(r.get('score', 0) for r in results) / len(results) if results else 0
    
    status_text = (
        f"🖥 <b>СТАТУС СИСТЕМЫ:</b>\n"
        f"✅ Аптайм: <code>{uptime}</code>\n"
        f"📁 Всего тестов: <b>{len(results)}</b>\n"
        f"📈 Средний балл: <b>{avg_score:.1f}/17</b>\n"
        f"🚀 Версия: {VERSION}"
    )
    bot.send_message(message.chat.id, status_text, parse_mode='html')

@bot.message_handler(func=lambda message: message.text == "📢 Отправить сообщение")
def ask_message(message):
    if not is_admin(message):
        return
    global admin_waiting_for_message
    admin_waiting_for_message = True
    bot.send_message(message.chat.id, "📝 Напиши сообщение для доски объявлений (появится на сайте):")

@bot.message_handler(func=lambda message: message.text == "🗑️ Очистить доску")
def clear_board(message):
    if not is_admin(message):
        return
    clear_messages()
    bot.send_message(message.chat.id, "✅ Доска объявлений очищена!")

@bot.message_handler(func=lambda message: message.text == "⚠️ Трудные вопросы")
def show_errors(message):
    if not is_admin(message):
        return
    
    error_report = get_top_errors_report()
    bot.send_message(message.chat.id, error_report, parse_mode='html')

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and not message.text.startswith('/'))
def handle_admin_input(message):
    global admin_waiting_for_message
    
    if admin_waiting_for_message:
        save_message(message.text)
        bot.send_message(message.chat.id, f"✅ Сообщение отправлено на доску!\n\n📝 {message.text}")
        admin_waiting_for_message = False
        bot.send_message(message.chat.id, "Выбери действие:", reply_markup=main_keyboard())

# --- API ДЛЯ САЙТА ---
@app.route('/send_result', methods=['POST', 'GET'])
def receive_result():
    if request.method == 'GET':
        return jsonify({"status": "online", "version": VERSION}), 200

    try:
        data = request.json
        name = data.get('name', 'Аноним')
        score = data.get('score', 0)
        wrong_qs = data.get('wrong_questions', [])
        
        answer_times = data.get('answer_times', {})
        suspicious_data = {
            'answers': data.get('suspicious_answers', 0),
            'avg_time': answer_times.get('average_time', 0),
            'suspicious_percent': answer_times.get('suspicious_percent', 0),
            'is_suspicious': float(answer_times.get('suspicious_percent', 0)) > 30
        }
        
        time_now = datetime.now().strftime("%d.%m %H:%M")

        save_result_to_file(name, score, time_now, suspicious_data)
        save_errors(wrong_qs)

        flag = "⚠️ ПОДОЗРЕНИЕ:" if suspicious_data['is_suspicious'] else "✅"
        msg = f"{flag} <b>НОВЫЙ РЕЗУЛЬТАТ!</b>\n"
        msg += f"👤 Имя: {name}\n"
        msg += f"✅ Баллы: {score}/17\n"
        
        if wrong_qs:
            msg += f"❌ Ошибки: {', '.join(map(str, wrong_qs))}\n"
        
        if suspicious_data['is_suspicious']:
            msg += f"⏱ Среднее время ответа: {suspicious_data['avg_time']}с\n"
            msg += f"🚨 Подозрительных ответов: {suspicious_data['answers']}\n"
        
        bot.send_message(ADMIN_ID, msg, parse_mode='html')
        
        return jsonify({"status": "success", "message": "Спасибо за результат!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_results', methods=['GET'])
def get_results():
    results = load_results()
    return jsonify({
        "total": len(results),
        "average_score": sum(r.get('score', 0) for r in results) / len(results) if results else 0,
        "recent": results[-5:] if results else []
    }), 200

@app.route('/admin_message', methods=['GET'])
def get_admin_messages():
    try:
        messages = load_messages()
        return jsonify({
            "status": "success",
            "messages": messages
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ЗАПУСК ---
def run_bot():
    print("🤖 Бот запущен...")
    bot.remove_webhook()
    bot.polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask запущен на порту {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
