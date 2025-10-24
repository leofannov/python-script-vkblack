import imaplib
import email
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging
import time
import json
import os
import socket
import threading
import requests

# Конфигурация
IMAP_SERVER = ""
IMAP_PORT = 993
SMTP_SERVER = ""
SMTP_PORT = 465
EMAIL = ""
PASSWORD = ""
TELEGRAM_TOKEN = ""
ALLOWED_USER_IDS = []  # Разрешённые ID пользователей/групп
CHECK_INTERVAL = 60  # Интервал проверки почты (секунды)
BLOCKED_EMAILS_FILE = "blocked_emails.json"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

blocked_emails = set()
user_states = {}

def load_blocked_emails():
    global blocked_emails
    if os.path.exists(BLOCKED_EMAILS_FILE):
        try:
            with open(BLOCKED_EMAILS_FILE, 'r') as f:
                data = json.load(f)
                blocked_emails = set(data.get('blocked_emails', []))
                logging.info(f"Загружено {len(blocked_emails)} заблокированных email")
        except Exception as e:
            logging.error(f"Ошибка загрузки файла блокировок: {e}")

def save_blocked_emails():
    try:
        data = {'blocked_emails': list(blocked_emails)}
        with open(BLOCKED_EMAILS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения файла блокировок: {e}")

def decode_subject(subject):
    """Декодирует тему письма из различных кодировок"""
    if not subject:
        return "Без темы"
    
    try:
        decoded = decode_header(subject)
        subject_parts = []
        for part, encoding in decoded:
            if isinstance(part, bytes):
                try:
                    subject_parts.append(part.decode(encoding if encoding else 'utf-8'))
                except:
                    subject_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                subject_parts.append(part)
        return "".join(subject_parts)
    except:
        return subject if subject else "Без темы"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("Доступ запрещен")
        return
    
    await update.message.reply_text("🤖 Бот запущен. Ожидание писем...")

async def test_smtp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("Доступ запрещен")
        return
    
    test_email = context.args[0] if context.args else EMAIL
    await update.message.reply_text(f"🧪 Тестируем SMTP отправку на {test_email}...")
    
    def test_send():
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(EMAIL, PASSWORD)
                
                msg = MIMEMultipart()
                msg["From"] = EMAIL
                msg["To"] = test_email
                msg["Subject"] = "Тест SMTP от бота"
                msg.attach(MIMEText("Это тестовое сообщение от Telegram бота", "plain"))
                
                server.sendmail(EMAIL, test_email, msg.as_string())
                logging.info(f"✅ Тестовое письмо отправлено на {test_email}")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка отправки: {e}")
        return False
    
    success = test_send()
    if success:
        await update.message.reply_text("✅ Тест SMTP пройден успешно!")
    else:
        await update.message.reply_text("❌ Ошибка SMTP. Проверьте логи.")

async def unblock_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для разблокировки email"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        await update.message.reply_text("Доступ запрещен")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /unblock <email>")
        return
    
    email_addr = context.args[0].lower()
    if email_addr in blocked_emails:
        blocked_emails.remove(email_addr)
        save_blocked_emails()
        await update.message.reply_text(f"Email {email_addr} разблокирован ✅")
    else:
        await update.message.reply_text(f"Email {email_addr} не найден в списке заблокированных")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    action = data[0]
    
    if action == "reply":
        from_email = data[1]
        user_states[query.from_user.id] = ("awaiting_reply", from_email)
        await query.edit_message_text(text="Введите ваш ответ:")
    
    elif action == "ignore":
        await query.edit_message_text(text="Письмо проигнорировано")
    
    elif action == "block":
        from_email = data[1]
        blocked_emails.add(from_email)
        save_blocked_emails()
        await query.edit_message_text(text=f"Email {from_email} заблокирован ✅")
    
    elif action == "unblock":
        email_addr = data[1]
        if email_addr in blocked_emails:
            blocked_emails.remove(email_addr)
            save_blocked_emails()
            await query.edit_message_text(text=f"Email {email_addr} разблокирован ✅")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states or user_states[user_id][0] != "awaiting_reply":
        return
    
    action, to_email = user_states[user_id]
    response_text = update.message.text
    
    def send_email():
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(EMAIL, PASSWORD)
                
                msg = MIMEMultipart()
                msg["From"] = EMAIL
                msg["To"] = to_email
                msg["Subject"] = "Ответ из Telegram бота"
                msg.attach(MIMEText(response_text, "plain"))
                
                server.sendmail(EMAIL, to_email, msg.as_string())
                logging.info(f"✅ Ответ отправлен на {to_email}")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка отправки ответа: {e}")
            return False
    
    success = send_email()
    if success:
        await update.message.reply_text("✅ Ответ отправлен!")
    else:
        await update.message.reply_text("❌ Ошибка отправки. Проверьте логи.")
    
    user_states[user_id] = None

def check_emails():
    """Проверка почты"""
    while True:
        try:
            with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as mail:
                mail.login(EMAIL, PASSWORD)
                mail.select("inbox")
                
                status, messages = mail.search(None, "UNSEEN")
                if status == "OK" and messages[0]:
                    email_ids = messages[0].split()
                    logging.info(f"📨 Найдено {len(email_ids)} новых писем")
                    
                    for eid in email_ids:
                        status, msg_data = mail.fetch(eid, "(RFC822)")
                        if status == "OK":
                            msg = email.message_from_bytes(msg_data[0][1])
                            from_email = email.utils.parseaddr(msg["From"])[1]
                            
                            # Декодируем тему письма
                            subject = decode_subject(msg.get("Subject", ""))
                            
                            if from_email in blocked_emails:
                                logging.info(f"⏭️ Пропущено письмо от заблокированного: {from_email}")
                                continue
                            
                            # Получаем текст письма
                            text = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        text = part.get_payload(decode=True).decode(errors='ignore')
                                        break
                            else:
                                text = msg.get_payload(decode=True).decode(errors='ignore')
                            
                            text = text or "Не удалось прочитать текст"
                            
                            # Отправляем в Telegram
                            send_telegram_notification(from_email, subject, text[:500])
                            
        except Exception as e:
            logging.error(f"Ошибка проверки почты: {e}")
            time.sleep(10)
        
        time.sleep(CHECK_INTERVAL)

def send_telegram_notification(from_email, subject, text):
    """Отправка уведомления в Telegram"""
    try:
        keyboard = [
            [{"text": "📨 Ответить", "callback_data": f"reply:{from_email}"}],
            [{"text": "❌ Игнорировать", "callback_data": "ignore"}],
            [{"text": "🚫 Заблокировать", "callback_data": f"block:{from_email}"}]
        ]
        
        message = f"📩 *Новое письмо*\n\n*От:* {from_email}\n*Тема:* {subject}\n\n{text}"
        
        for user_id in ALLOWED_USER_IDS:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": user_id,
                "text": message,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": keyboard
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logging.info(f"📤 Уведомление отправлено пользователю {user_id}")
            else:
                logging.error(f"❌ Ошибка Telegram API: {response.text}")
                
    except Exception as e:
        logging.error(f"❌ Ошибка отправки в Telegram: {e}")

if __name__ == "__main__":
    load_blocked_emails()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_smtp))
    app.add_handler(CommandHandler("unblock", unblock_email))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    email_thread = threading.Thread(target=check_emails, daemon=True)
    email_thread.start()
    
    logging.info("🤖 Бот запущен. Ожидание новых писем...")
    app.run_polling()
