import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import threading
import time
from datetime import datetime
import sys
import logging
import requests
import json

# Конфигурация
ACCOUNTS = [
    "",
]

ALLOWED_USERS = []
SUPPORT_EMAIL = ""
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_ALLOWED_IDS = []  # Замените на ID пользователей/групп Telegram

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные флаги управления
BOT_ENABLED = True
ACCOUNT_STATUS = {i: True for i in range(len(ACCOUNTS))}

class VKBot:
    def __init__(self, token, account_index):
        self.token = token
        self.account_index = account_index
        self.vk_session = None
        self.vk = None
        self.longpoll = None
        self.start_time = datetime.now()
        self.processed_messages = set()
        self.processed_requests = set()
        self.processed_subscribes = set()
        self.initialize_vk()
        
    def initialize_vk(self):
        """Инициализация VK API с обработкой ошибок"""
        try:
            self.vk_session = vk_api.VkApi(token=self.token)
            self.vk = self.vk_session.get_api()
            self.longpoll = VkLongPoll(self.vk_session)
            logger.info(f"Аккаунт {self.account_index} успешно инициализирован")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации аккаунта {self.account_index}: {e}")
            return False
    
    def get_uptime(self):
        return str(datetime.now() - self.start_time).split('.')[0]
    
    def get_user_name(self, user_id):
        try:
            user = self.vk.users.get(user_ids=user_id)[0]
            return f"{user['first_name']} {user['last_name']}"
        except:
            return "Неизвестный пользователь"
    
    def send_message_and_block(self, user_id, message):
        try:
            # Отправляем сообщение
            self.vk.messages.send(
                user_id=user_id,
                message=message,
                random_id=vk_api.utils.get_random_id()
            )
            
            # Блокируем пользователя
            self.vk.account.ban(owner_id=user_id)
            logger.info(f"Пользователь {user_id} заблокирован аккаунтом {self.account_index}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки/блокировки аккаунтом {self.account_index}: {e}")
    
    def check_existing_data(self):
        """Проверяем существующие сообщения, заявки и подписки при запуске"""
        if not ACCOUNT_STATUS[self.account_index]:
            return
            
        logger.info(f"Аккаунт {self.account_index} проверяет существующие сообщения...")
        try:
            messages = self.vk.messages.getConversations(count=50)['items']
            for conv in messages:
                msg = conv['last_message']
                if (msg['from_id'] in ALLOWED_USERS and 
                    msg['id'] not in self.processed_messages and
                    not msg.get('out', 0)):
                    
                    user_name = self.get_user_name(msg['from_id'])
                    response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении и ее подруг (то есть, вас) от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {self.get_uptime()}
Сервис ПО "Защита информации от" """
                    
                    self.send_message_and_block(msg['from_id'], response)
                    self.processed_messages.add(msg['id'])
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке сообщений аккаунтом {self.account_index}: {e}")
        
        logger.info(f"Аккаунт {self.account_index} проверяет существующие заявки в друзья...")
        try:
            requests = self.vk.friends.getRequests()
            if 'items' in requests:
                for user_id in requests['items']:
                    if user_id in ALLOWED_USERS and user_id not in self.processed_requests:
                        user_name = self.get_user_name(user_id)
                        response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {self.get_uptime()}
Сервис ПО "Защита информации от " """
                        
                        self.send_message_and_block(user_id, response)
                        self.processed_requests.add(user_id)
                        
        except Exception as e:
            logger.error(f"Ошибка при проверке заявок аккаунтом {self.account_index}: {e}")
        
        logger.info(f"Аккаунт {self.account_index} проверяет существующие подписки...")
        try:
            # Получаем подписчиков
            followers = self.vk.users.getFollowers(count=100)
            if 'items' in followers:
                for user_id in followers['items']:
                    if user_id in ALLOWED_USERS and user_id not in self.processed_subscribes:
                        user_name = self.get_user_name(user_id)
                        response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении и ее подруг (то есть, вас) от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {self.get_uptime()}
Сервис ПО "Защита информации от" """
                        
                        self.send_message_and_block(user_id, response)
                        self.processed_subscribes.add(user_id)
                        
        except Exception as e:
            logger.error(f"Ошибка при проверке подписок аккаунтом {self.account_index}: {e}")
    
    def run(self):
        logger.info(f"Бот запущен для аккаунта {self.account_index}")
        
        # Проверяем существующие данные при запуске
        self.check_existing_data()
        
        logger.info(f"Аккаунт {self.account_index} ожидает новые события...")
        
        # Слушаем новые события в реальном времени с переподключением при ошибках
        while True:
            if not ACCOUNT_STATUS[self.account_index]:
                time.sleep(10)
                continue
                
            try:
                for event in self.longpoll.listen():
                    if not ACCOUNT_STATUS[self.account_index]:
                        break
                        
                    try:
                        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                            # Новое сообщение
                            if event.user_id in ALLOWED_USERS and event.message_id not in self.processed_messages:
                                user_name = self.get_user_name(event.user_id)
                                response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении и ее подруг (то есть, вас) от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {self.get_uptime()}
Сервис ПО "Защита информации от" """
                                
                                self.send_message_and_block(event.user_id, response)
                                self.processed_messages.add(event.message_id)
                                logger.info(f"Аккаунт {self.account_index} обработал новое сообщение от {event.user_id}")
                    
                    except Exception as e:
                        logger.error(f"Ошибка обработки события аккаунтом {self.account_index}: {e}")
                        time.sleep(5)
                        
            except Exception as e:
                logger.error(f"Ошибка longpoll аккаунта {self.account_index}: {e}")
                logger.info(f"Переподключение аккаунта {self.account_index} через 10 секунд...")
                time.sleep(10)
                # Пытаемся переинициализировать соединение
                if not self.initialize_vk():
                    time.sleep(60)  # Ждем дольше при ошибке инициализации

def check_requests_and_subscribes_periodically(bot):
    """Периодическая проверка заявок в друзья и подписок"""
    while True:
        if not ACCOUNT_STATUS[bot.account_index]:
            time.sleep(10)
            continue
            
        try:
            # Проверяем заявки в друзья
            requests = bot.vk.friends.getRequests()
            if 'items' in requests:
                for user_id in requests['items']:
                    if user_id in ALLOWED_USERS and user_id not in bot.processed_requests:
                        user_name = bot.get_user_name(user_id)
                        response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении и ее подруг (то есть, вас) от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {bot.get_uptime()}
Сервис ПО "Защита информации от" """
                        
                        bot.send_message_and_block(user_id, response)
                        bot.processed_requests.add(user_id)
                        logger.info(f"Аккаунт {bot.account_index} обработал новую заявку от {user_id}")
            
            # Проверяем новые подписки
            followers = bot.vk.users.getFollowers(count=100)
            if 'items' in followers:
                for user_id in followers['items']:
                    if user_id in ALLOWED_USERS and user_id not in bot.processed_subscribes:
                        user_name = bot.get_user_name(user_id)
                        response = f"""Здравствуйте, {user_name}, в связи с веденными ограничениями в отношении и ее подруг (то есть, вас) от 24 февраля 2025 г., вам запрещается писать в личные сообщения, для связи используйте {SUPPORT_EMAIL}

Версия Python: {sys.version}
Uptime: {bot.get_uptime()}
Сервис ПО "Защита информации от" """
                        
                        bot.send_message_and_block(user_id, response)
                        bot.processed_subscribes.add(user_id)
                        logger.info(f"Аккаунт {bot.account_index} обработал новую подписку от {user_id}")
            
            time.sleep(10)  # Проверяем каждые 10 секунд
            
        except Exception as e:
            logger.error(f"Ошибка проверки заявок/подписок аккаунтом {bot.account_index}: {e}")
            time.sleep(30)

# Telegram бот через синхронные запросы
class TelegramBot:
    def __init__(self, token, allowed_ids):
        self.token = token
        self.allowed_ids = allowed_ids
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        
    def send_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения через Telegram API"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
            return None
            
    def edit_message_text(self, chat_id, message_id, text, reply_markup=None):
        """Редактирование сообщения через Telegram API"""
        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения в Telegram: {e}")
            return None
            
    def get_updates(self):
        """Получение обновлений от Telegram API"""
        url = f"{self.base_url}/getUpdates"
        params = {
            "timeout": 30,
            "offset": self.last_update_id + 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                return data["result"]
            return []
        except Exception as e:
            logger.error(f"Ошибка получения обновлений от Telegram: {e}")
            return []
            
    def answer_callback_query(self, callback_query_id, text=None):
        """Ответ на callback запрос"""
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id
        }
        
        if text:
            payload["text"] = text
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка ответа на callback: {e}")
            return None
            
    def process_updates(self):
        """Обработка обновлений от Telegram"""
        updates = self.get_updates()
        
        for update in updates:
            self.last_update_id = update["update_id"]
            
            # Обработка callback запросов
            if "callback_query" in update:
                callback_query = update["callback_query"]
                user_id = callback_query["from"]["id"]
                
                if user_id not in self.allowed_ids:
                    self.answer_callback_query(callback_query["id"], "Доступ запрещен")
                    continue
                    
                data = callback_query["data"]
                message = callback_query["message"]
                
                global BOT_ENABLED, ACCOUNT_STATUS
                
                if data == "status":
                    status_text = f"Общий статус: {'ВКЛЮЧЕН' if BOT_ENABLED else 'ВЫКЛЮЧЕН'}\n"
                    for i, status in ACCOUNT_STATUS.items():
                        status_text += f"Аккаунт {i}: {'ВКЛЮЧЕН' if status else 'ВЫКЛЮЧЕН'}\n"
                    
                    keyboard = [[{"text": "Назад", "callback_data": "back"}]]
                    reply_markup = {"inline_keyboard": keyboard}
                    
                    self.edit_message_text(
                        message["chat"]["id"],
                        message["message_id"],
                        status_text,
                        reply_markup
                    )
                    self.answer_callback_query(callback_query["id"])
                    
                elif data == "enable_all":
                    BOT_ENABLED = True
                    for i in range(len(ACCOUNTS)):
                        ACCOUNT_STATUS[i] = True
                    
                    self.edit_message_text(
                        message["chat"]["id"],
                        message["message_id"],
                        "Все аккаунты включены"
                    )
                    self.answer_callback_query(callback_query["id"])
                    
                elif data == "disable_all":
                    BOT_ENABLED = False
                    for i in range(len(ACCOUNTS)):
                        ACCOUNT_STATUS[i] = False
                    
                    self.edit_message_text(
                        message["chat"]["id"],
                        message["message_id"],
                        "Все аккаунты выключены"
                    )
                    self.answer_callback_query(callback_query["id"])
                    
                elif data == "back":
                    keyboard = [
                        [{"text": "Статус", "callback_data": "status"}],
                        [{"text": "Включить все", "callback_data": "enable_all"}, 
                         {"text": "Выключить все", "callback_data": "disable_all"}],
                    ]
                    reply_markup = {"inline_keyboard": keyboard}
                    
                    self.edit_message_text(
                        message["chat"]["id"],
                        message["message_id"],
                        "Выберите действие:",
                        reply_markup
                    )
                    self.answer_callback_query(callback_query["id"])
                    
                elif data.startswith("acc_"):
                    parts = data.split("_")
                    acc_index = int(parts[1])
                    action = parts[2]
                    
                    if action == "enable":
                        ACCOUNT_STATUS[acc_index] = True
                        self.edit_message_text(
                            message["chat"]["id"],
                            message["message_id"],
                            f"Аккаунт {acc_index} включен"
                        )
                    elif action == "disable":
                        ACCOUNT_STATUS[acc_index] = False
                        self.edit_message_text(
                            message["chat"]["id"],
                            message["message_id"],
                            f"Аккаунт {acc_index} выключен"
                        )
                    
                    self.answer_callback_query(callback_query["id"])
            
            # Обработка текстовых сообщений
            elif "message" in update and "text" in update["message"]:
                message = update["message"]
                user_id = message["from"]["id"]
                text = message["text"]
                
                if user_id not in self.allowed_ids:
                    self.send_message(message["chat"]["id"], "Доступ запрещен")
                    continue
                    
                if text == "/start":
                    keyboard = [
                        [{"text": "Статус", "callback_data": "status"}],
                        [{"text": "Включить все", "callback_data": "enable_all"}, 
                         {"text": "Выключить все", "callback_data": "disable_all"}],
                    ]
                    reply_markup = {"inline_keyboard": keyboard}
                    
                    self.send_message(
                        message["chat"]["id"],
                        "Выберите действие:",
                        reply_markup
                    )
                    
                elif text == "/accounts":
                    keyboard = []
                    for i in range(len(ACCOUNTS)):
                        keyboard.append([
                            {"text": f"Аккаунт {i}", "callback_data": f"acc_{i}_info"},
                            {"text": "Вкл", "callback_data": f"acc_{i}_enable"},
                            {"text": "Выкл", "callback_data": f"acc_{i}_disable"}
                        ])
                    
                    keyboard.append([{"text": "Назад", "callback_data": "back"}])
                    reply_markup = {"inline_keyboard": keyboard}
                    
                    self.send_message(
                        message["chat"]["id"],
                        "Управление аккаунтами:",
                        reply_markup
                    )
    
    def run(self):
        """Запуск Telegram бота"""
        logger.info("Telegram бот запущен")
        
        while True:
            try:
                self.process_updates()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка в Telegram боте: {e}")
                time.sleep(5)

# Запускаем ботов
if __name__ == "__main__":
    # Запускаем Telegram бота в отдельном потоке
    telegram_bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_IDS)
    telegram_thread = threading.Thread(target=telegram_bot.run, daemon=True)
    telegram_thread.start()
    
    # Запускаем VK ботов
    vk_bots = []
    threads = []
    
    for i, token in enumerate(ACCOUNTS):
        try:
            bot = VKBot(token, i)
            vk_bots.append(bot)
            
            # Запускаем основной поток для сообщений через LongPoll
            main_thread = threading.Thread(target=bot.run)
            main_thread.daemon = True
            main_thread.start()
            
            # Запускаем поток для периодической проверки заявок и подписок
            check_thread = threading.Thread(target=check_requests_and_subscribes_periodically, args=(bot,))
            check_thread.daemon = True
            check_thread.start()
            
            threads.append((main_thread, check_thread))
            logger.info(f"Запущен бот для аккаунта {i}")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота для аккаунта {i}: {e}")

    # Основной цикл
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка ботов...")
