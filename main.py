import telebot
import psycopg2
from datetime import datetime

TOKEN = ''  
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = '1234'
DB_HOST = 'localhost'
DB_PORT = '5432'

bot = telebot.TeleBot(TOKEN)

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        options='-c client_encoding=UTF8'
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            deadline DATE,
            priority TEXT CHECK (priority IN ('past', 'o‘rta', 'yuqori')),
            status TEXT DEFAULT 'Bajarilmoqda'
        );
    """)
    conn.commit()
    print("✅ Jadval tayyor.")
except Exception as e:
    print(f"❌ Xatolik: {e}")
    exit()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Salom! Vazifalar boshqaruvchisi botiga xush kelibsiz! /help buyrug'ini bosing.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "Quyidagi buyruqlarni ishlatishingiz mumkin:\n"
        "/start - Botni ishga tushirish\n"
        "/mytasks - Mening vazifalarim\n"
        "/newtask - Yangi vazifa yaratish\n"
        "/updatetask - Vazifani yangilash\n"
        "/deletetask - Vazifani o'chirish\n"
        "/manage_task - Vazifani boshqarish (yangilash yoki o'chirish)\n"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['newtask'])
def new_task(message):
    msg = bot.send_message(message.chat.id, "✏️ Vazifa nomini kiriting:")
    bot.register_next_step_handler(msg, process_task_name)

def process_task_name(message):
    task_name = message.text
    msg = bot.send_message(message.chat.id, "📄 Vazifa tavsifini kiriting:")
    bot.register_next_step_handler(msg, process_task_description, task_name)

def process_task_description(message, task_name):
    task_description = message.text
    msg = bot.send_message(message.chat.id, "📅 Deadline (YYYY-MM-DD):")
    bot.register_next_step_handler(msg, process_task_deadline, task_name, task_description)

def process_task_deadline(message, task_name, task_description):
    task_deadline = message.text
    try:
        deadline_date = datetime.strptime(task_deadline, "%Y-%m-%d").date()
        msg = bot.send_message(message.chat.id, "⚙️ Prioritetni tanlang (past / o‘rta / yuqori):")
        bot.register_next_step_handler(msg, process_task_priority, task_name, task_description, deadline_date)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Noto‘g‘ri sana formati! Iltimos, YYYY-MM-DD shaklida kiriting:")
        bot.register_next_step_handler(msg, process_task_deadline, task_name, task_description)

def process_task_priority(message, task_name, task_description, task_deadline):
    task_priority = message.text.lower()
    if task_priority not in ['past', 'o‘rta', 'yuqori']:
        msg = bot.send_message(message.chat.id, "❌ Noto‘g‘ri prioritet! Iltimos, past / o‘rta / yuqori deb yozing:")
        bot.register_next_step_handler(msg, process_task_priority, task_name, task_description, task_deadline)
        return
    try:
        cursor.execute(
            'INSERT INTO tasks (user_id, name, description, deadline, priority, status) VALUES (%s, %s, %s, %s, %s, %s)',
            (message.from_user.id, task_name, task_description, task_deadline, task_priority, 'Bajarilmoqda')
        )
        conn.commit()
        bot.send_message(message.chat.id, "✅ Vazifa yaratildi!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['mytasks'])
def my_tasks(message):
    user_id = message.from_user.id
    cursor.execute('SELECT id, name, description, deadline, priority, status FROM tasks WHERE user_id = %s', (user_id,))
    tasks = cursor.fetchall()

    if not tasks:
        bot.send_message(message.chat.id, "Sizda hali hech qanday vazifa mavjud emas.")
        return

    response = "📝 Sizning vazifalaringiz:\n\n"
    for task in tasks:
        task_id, name, description, deadline, priority, status = task
        response += (
            f"🔹 ID: {task_id}\n"
            f"📌 Nomi: {name}\n"
            f"📄 Tavsifi: {description}\n"
            f"📅 Deadline: {deadline}\n"
            f"⚙️ Prioritet: {priority}\n"
            f"📍 Status: {status}\n\n"
        )
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['updatetask'])
def update_task(message):
    msg = bot.send_message(message.chat.id, "✏️ Yangilamoqchi bo‘lgan vazifa ID sini kiriting:")
    bot.register_next_step_handler(msg, process_update_id)

def process_update_id(message):
    task_id = message.text
    msg = bot.send_message(message.chat.id, "🆕 Yangi nomini kiriting:")
    bot.register_next_step_handler(msg, process_update_name, task_id)

def process_update_name(message, task_id):
    new_name = message.text
    msg = bot.send_message(message.chat.id, "📄 Yangi tavsifni kiriting:")
    bot.register_next_step_handler(msg, process_update_description, task_id, new_name)

def process_update_description(message, task_id, new_name):
    new_description = message.text
    try:
        cursor.execute('UPDATE tasks SET name = %s, description = %s WHERE id = %s', (new_name, new_description, task_id))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Vazifa yangilandi!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['deletetask'])
def delete_task(message):
    msg = bot.send_message(message.chat.id, "🗑 O‘chirmoqchi bo‘lgan vazifa ID sini kiriting:")
    bot.register_next_step_handler(msg, process_delete_task)

def process_delete_task(message):
    task_id = message.text
    try:
        cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (task_id, message.from_user.id))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Vazifa o‘chirildi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['manage_task'])
def manage_task(message):
    msg = bot.send_message(message.chat.id, "🔢 Vazifa ID sini kiriting:")
    bot.register_next_step_handler(msg, process_manage_task_id)

def process_manage_task_id(message):
    task_id = message.text
    msg = bot.send_message(message.chat.id, "⚙️ 'yangilash' yoki 'o'chirish' deb yozing:")
    bot.register_next_step_handler(msg, process_manage_action, task_id)

def process_manage_action(message, task_id):
    action = message.text.lower()
    if action == "yangilash":
        msg = bot.send_message(message.chat.id, "✏️ Yangi vazifa nomi:")
        bot.register_next_step_handler(msg, process_update_task_name, task_id)
    elif action == "o'chirish":
        try:
            cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (task_id, message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id, "🗑 Vazifa o'chirildi.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {e}")
    else:
        bot.send_message(message.chat.id, "❗ Noto'g'ri tanlov.")

def process_update_task_name(message, task_id):
    new_name = message.text
    msg = bot.send_message(message.chat.id, "📄 Yangi tavsif:")
    bot.register_next_step_handler(msg, process_update_task_description, task_id, new_name)

def process_update_task_description(message, task_id, new_name):
    new_desc = message.text
    try:
        cursor.execute(
            'UPDATE tasks SET name = %s, description = %s WHERE id = %s',
            (new_name, new_desc, task_id)
        )
        conn.commit()
        bot.send_message(message.chat.id, "✅ Vazifa yangilandi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

print("🚀 Bot ishga tushdi...")
bot.polling()
