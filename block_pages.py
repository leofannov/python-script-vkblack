import os
import logging
from typing import Dict, List
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import vk_api

# Настройки
BOT_TOKEN = ''
ALLOWED_USERS = []  # ID разрешенных пользователей Telegram
VK_TOKENS = ['']  # Токены VK аккаунтов
ALLOWED_VK_IDS = []  # ID VK пользователей, которых можно банить/разбанить

# Состояния для ConversationHandler
ADDING_VK = 1
CHOOSING_ACCOUNT = 2
CHOOSING_USER_FOR_ACCOUNT = 3

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

class VKManager:
    def __init__(self, tokens: List[str]):
        self.sessions = []
        for token in tokens:
            try:
                vk_session = vk_api.VkApi(token=token)
                self.sessions.append(vk_session.get_api())
            except Exception as e:
                logging.error(f"Информация инициализации VK API: {e}")
    
    def get_account_info(self):
        """Получение информации о VK аккаунтах"""
        accounts_info = []
        for i, vk in enumerate(self.sessions):
            try:
                info = vk.users.get()[0]
                name = f"{info.get('first_name', 'Неизвестно')} {info.get('last_name', 'Неизвестно')}"
                accounts_info.append(f"Аккаунт {i+1}: {name}")
            except Exception as e:
                accounts_info.append(f"Аккаунт {i+1}: Ошибка получения информации - {str(e)}")
        return accounts_info
    
    def get_user_info(self, user_id: int):
        """Получение информации о пользователе VK"""
        if not self.sessions:
            return "Не удалось получить информацию: нет активных сессий VK"
        
        try:
            user_info = self.sessions[0].users.get(user_ids=user_id, fields="first_name,last_name")
            if user_info and isinstance(user_info, list) and len(user_info) > 0:
                user = user_info[0]
                return f"{user.get('first_name', 'Неизвестно')} {user.get('last_name', 'Неизвестно')}"
            return "Неизвестный пользователь"
        except Exception as e:
            return f"Не удалось получить информацию: {str(e)}"
    
    def ban_user(self, user_id: int, account_index: int = None):
        """Бан пользователя с возможностью выбора конкретного аккаунта"""
        user_info = self.get_user_info(user_id)
        results = [f"Пользователь: {user_info} (ID: {user_id})"]
        
        if account_index is not None:
            # Бан на конкретном аккаунте
            if 0 <= account_index < len(self.sessions):
                try:
                    result = self.sessions[account_index].account.ban(owner_id=user_id)
                    results.append(f"Аккаунт {account_index+1}: Заблокирован успешно")
                except Exception as e:
                    results.append(f"Аккаунт {account_index+1}: Информация - {str(e)}")
            else:
                results.append("Неверный номер аккаунта")
        else:
            # Бан на всех аккаунтах
            for i, vk in enumerate(self.sessions):
                try:
                    result = vk.account.ban(owner_id=user_id)
                    results.append(f"Аккаунт {i+1}: Заблокирован успешно")
                except Exception as e:
                    results.append(f"Аккаунт {i+1}: Информация - {str(e)}")
        return results
    
    def unban_user(self, user_id: int, account_index: int = None):
        """Разбан пользователя с возможностью выбора конкретного аккаунта"""
        user_info = self.get_user_info(user_id)
        results = [f"Пользователь: {user_info} (ID: {user_id})"]
        
        if account_index is not None:
            # Разбан на конкретном аккаунте
            if 0 <= account_index < len(self.sessions):
                try:
                    result = self.sessions[account_index].account.unban(owner_id=user_id)
                    results.append(f"Аккаунт {account_index+1}: Разблокирован успешно")
                except Exception as e:
                    results.append(f"Аккаунт {account_index+1}: Информация - {str(e)}")
            else:
                results.append("Неверный номер аккаунта")
        else:
            # Разбан на всех аккаунтах
            for i, vk in enumerate(self.sessions):
                try:
                    result = vk.account.unban(owner_id=user_id)
                    results.append(f"Аккаунт {i+1}: Разблокирован успешно")
                except Exception as e:
                    results.append(f"Аккаунт {i+1}: Информация - {str(e)}")
        return results
    
    def mass_ban(self, account_index: int = None):
        """Массовый бан всех пользователей из списка с возможностью выбора аккаунта"""
        results = ["Массовый бан:"]
        
        if account_index is not None:
            # Бан на конкретном аккаунте
            if 0 <= account_index < len(self.sessions):
                for user_id in ALLOWED_VK_IDS:
                    user_info = self.get_user_info(user_id)
                    results.append(f"\nПользователь: {user_info} (ID: {user_id})")
                    
                    try:
                        self.sessions[account_index].account.ban(owner_id=user_id)
                        results.append(f"  Аккаунт {account_index+1}: Заблокирован")
                    except Exception as e:
                        results.append(f"  Аккаунт {account_index+1}: Информация - {str(e)}")
            else:
                results.append("Неверный номер аккаунта")
        else:
            # Бан на всех аккаунтах
            for user_id in ALLOWED_VK_IDS:
                user_info = self.get_user_info(user_id)
                results.append(f"\nПользователь: {user_info} (ID: {user_id})")
                
                for i, vk in enumerate(self.sessions):
                    try:
                        vk.account.ban(owner_id=user_id)
                        results.append(f"  Аккаунт {i+1}: Заблокирован")
                    except Exception as e:
                        results.append(f"  Аккаунт {i+1}: Информация - {str(e)}")
        return results
    
    def mass_unban(self, account_index: int = None):
        """Массовый разбан всех пользователей из списка с возможностью выбора аккаунта"""
        results = ["Массовый разбан:"]
        
        if account_index is not None:
            # Разбан на конкретном аккаунте
            if 0 <= account_index < len(self.sessions):
                for user_id in ALLOWED_VK_IDS:
                    user_info = self.get_user_info(user_id)
                    results.append(f"\nПользователь: {user_info} (ID: {user_id})")
                    
                    try:
                        self.sessions[account_index].account.unban(owner_id=user_id)
                        results.append(f"  Аккаунт {account_index+1}: Разблокирован")
                    except Exception as e:
                        results.append(f"  Аккаунт {account_index+1}: Информация - {str(e)}")
            else:
                results.append("Неверный номер аккаунта")
        else:
            # Разбан на всех аккаунтах
            for user_id in ALLOWED_VK_IDS:
                user_info = self.get_user_info(user_id)
                results.append(f"\nПользователь: {user_info} (ID: {user_id})")
                
                for i, vk in enumerate(self.sessions):
                    try:
                        vk.account.unban(owner_id=user_id)
                        results.append(f"  Аккаунт {i+1}: Разблокирован")
                    except Exception as e:
                        results.append(f"  Аккаунт {i+1}: Информация - {str(e)}")
        return results
    
    def get_banned(self, account_index: int = None):
        """Получение списка заблокированных пользователей с возможностью выбора аккаунта"""
        banned_list = ["Заблокированные пользователи:"]
        
        if account_index is not None:
            # Для конкретного аккаунта
            if 0 <= account_index < len(self.sessions):
                banned_list.append(f"\nАккаунт {account_index+1}:")
                try:
                    result = self.sessions[account_index].account.getBanned(count=200)
                    if hasattr(result, 'get') and callable(getattr(result, 'get')):
                        items = result.get('items', [])
                        if items and isinstance(items, list):
                            for item in items:
                                if hasattr(item, 'get') and callable(getattr(item, 'get')):
                                    user_id = item.get('id', 'Unknown')
                                    first_name = item.get('first_name', '')
                                    last_name = item.get('last_name', '')
                                    
                                    if first_name and last_name:
                                        banned_list.append(f"{first_name} {last_name} (ID: {user_id})")
                                    else:
                                        user_info = self.get_user_info(user_id)
                                        banned_list.append(f"{user_info} (ID: {user_id})")
                                else:
                                    user_info = self.get_user_info(item)
                                    banned_list.append(f"{user_info} (ID: {item})")
                        else:
                            banned_list.append("Информация: Нет заблокированных пользователей")
                    else:
                        banned_list.append("Информация: Неверный формат ответа от VK API")
                except Exception as e:
                    banned_list.append(f"Информация: {str(e)}")
            else:
                banned_list.append("Неверный номер аккаунта")
        else:
            # Для всех аккаунтов
            for i, vk in enumerate(self.sessions):
                banned_list.append(f"\nАккаунт {i+1}:")
                try:
                    result = vk.account.getBanned(count=200)
                    if hasattr(result, 'get') and callable(getattr(result, 'get')):
                        items = result.get('items', [])
                        if items and isinstance(items, list):
                            for item in items:
                                if hasattr(item, 'get') and callable(getattr(item, 'get')):
                                    user_id = item.get('id', 'Unknown')
                                    first_name = item.get('first_name', '')
                                    last_name = item.get('last_name', '')
                                    
                                    if first_name and last_name:
                                        banned_list.append(f"{first_name} {last_name} (ID: {user_id})")
                                    else:
                                        user_info = self.get_user_info(user_id)
                                        banned_list.append(f"{user_info} (ID: {user_id})")
                                else:
                                    user_info = self.get_user_info(item)
                                    banned_list.append(f"{user_info} (ID: {item})")
                        else:
                            banned_list.append("Информация: Нет заблокированных пользователей")
                    else:
                        banned_list.append("Информация: Неверный формат ответа от VK API")
                except Exception as e:
                    banned_list.append(f"Информация: {str(e)}")
        return banned_list

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Доступ запрещен")
        return
    
    # Очищаем состояние пользователя
    context.user_data.clear()
    
    keyboard = [
        ['Забанить всех', 'Разбанить всех'],
        ['Список ЧС', 'Добавить VK'],
        ['Забанить по одному', 'Разбанить по одному'],
        ['Информация об аккаунтах VK'],
        ['Массовые действия на аккаунте', 'Поштучные действия на аккаунте']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Доступ запрещен")
        return ConversationHandler.END
    
    text = update.message.text
    vk_manager = VKManager(VK_TOKENS)
    
    if text == "Добавить VK":
        await update.message.reply_text("Отправьте токен VK:")
        return ADDING_VK
    elif text == "Список ЧС":
        banned = vk_manager.get_banned()
        message = "\n".join(banned)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Забанить всех":
        results = vk_manager.mass_ban()
        message = "\n".join(results)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Разбанить всех":
        results = vk_manager.mass_unban()
        message = "\n".join(results)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Забанить по одному":
        keyboard = [[str(user_id)] for user_id in ALLOWED_VK_IDS]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите ID пользователя для бана:",
            reply_markup=reply_markup
        )
        context.user_data['action'] = 'ban'
        return ConversationHandler.END
    elif text == "Разбанить по одному":
        keyboard = [[str(user_id)] for user_id in ALLOWED_VK_IDS]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите ID пользователя для разбана:",
            reply_markup=reply_markup
        )
        context.user_data['action'] = 'unban'
        return ConversationHandler.END
    elif text == "Информация об аккаунтах VK":
        accounts_info = vk_manager.get_account_info()
        message = "\n".join(accounts_info)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Массовые действия на аккаунте":
        keyboard = [[f"Аккаунт {i+1}"] for i in range(len(VK_TOKENS))]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите аккаунт для массовых действий:",
            reply_markup=reply_markup
        )
        context.user_data['action_type'] = 'mass_account'
        return CHOOSING_ACCOUNT
    elif text == "Поштучные действия на аккаунте":
        keyboard = [[f"Аккаунт {i+1}"] for i in range(len(VK_TOKENS))]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите аккаунт для поштучных действий:",
            reply_markup=reply_markup
        )
        context.user_data['action_type'] = 'single_account'
        return CHOOSING_ACCOUNT
    elif text == "↩️ Назад":
        await start(update, context)
        return ConversationHandler.END
    elif 'action' in context.user_data:
        try:
            user_id = int(text)
            if user_id in ALLOWED_VK_IDS:
                if context.user_data['action'] == 'ban':
                    results = vk_manager.ban_user(user_id)
                else:
                    results = vk_manager.unban_user(user_id)
                message = "\n".join(results)
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("Этот ID не в списке разрешенных для управления")
        except ValueError:
            await update.message.reply_text("Неверный ID пользователя")
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    vk_manager = VKManager(VK_TOKENS)
    
    if text == "↩️ Назад":
        await start(update, context)
        return ConversationHandler.END
    
    if text.startswith("Аккаунт "):
        try:
            account_index = int(text.split(" ")[1]) - 1
            if 0 <= account_index < len(VK_TOKENS):
                context.user_data['account_index'] = account_index
                
                if context.user_data['action_type'] == 'mass_account':
                    keyboard = [
                        ['Забанить всех на аккаунте', 'Разбанить всех на аккаунте'],
                        ['Список ЧС на аккаунте'],
                        ['↩️ Назад']
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        f"Выбран аккаунт {account_index+1}. Выберите действие:",
                        reply_markup=reply_markup
                    )
                    return CHOOSING_USER_FOR_ACCOUNT
                else:
                    keyboard = [
                        ['Забанить на аккаунте', 'Разбанить на аккаунте'],
                        ['↩️ Назад']
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        f"Выбран аккаунт {account_index+1}. Выберите действие:",
                        reply_markup=reply_markup
                    )
                    return CHOOSING_USER_FOR_ACCOUNT
            else:
                await update.message.reply_text("Неверный номер аккаунта")
        except ValueError:
            await update.message.reply_text("Неверный формат номера аккаунта")
    
    return ConversationHandler.END

async def handle_account_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    vk_manager = VKManager(VK_TOKENS)
    account_index = context.user_data.get('account_index')
    
    if text == "↩️ Назад":
        # Возврат к выбору аккаунта
        keyboard = [[f"Аккаунт {i+1}"] for i in range(len(VK_TOKENS))]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        action_type = context.user_data.get('action_type')
        action_text = "массовых" if action_type == 'mass_account' else "поштучных"
        
        await update.message.reply_text(
            f"Выберите аккаунт для {action_text} действий:",
            reply_markup=reply_markup
        )
        return CHOOSING_ACCOUNT
    
    if account_index is None:
        await update.message.reply_text("Ошибка: не выбран аккаунт")
        return ConversationHandler.END
    
    if text == "Забанить всех на аккаунте":
        results = vk_manager.mass_ban(account_index)
        message = "\n".join(results)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Разбанить всех на аккаунте":
        results = vk_manager.mass_unban(account_index)
        message = "\n".join(results)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Список ЧС на аккаунте":
        banned = vk_manager.get_banned(account_index)
        message = "\n".join(banned)
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif text == "Забанить на аккаунте":
        context.user_data['action'] = 'ban_account_single'
        keyboard = [[str(user_id)] for user_id in ALLOWED_VK_IDS]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите ID пользователя для бана:",
            reply_markup=reply_markup
        )
        return CHOOSING_USER_FOR_ACCOUNT
    elif text == "Разбанить на аккаунте":
        context.user_data['action'] = 'unban_account_single'
        keyboard = [[str(user_id)] for user_id in ALLOWED_VK_IDS]
        keyboard.append(['↩️ Назад'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите ID пользователя для разбана:",
            reply_markup=reply_markup
        )
        return CHOOSING_USER_FOR_ACCOUNT
    elif 'action' in context.user_data and context.user_data['action'] in ['ban_account_single', 'unban_account_single']:
        try:
            user_id = int(text)
            if user_id in ALLOWED_VK_IDS:
                if context.user_data['action'] == 'ban_account_single':
                    results = vk_manager.ban_user(user_id, account_index)
                else:
                    results = vk_manager.unban_user(user_id, account_index)
                message = "\n".join(results)
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("Этот ID не в списке разрешенных для управления")
        except ValueError:
            await update.message.reply_text("Неверный ID пользователя")
        context.user_data.pop('action', None)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def add_vk_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "↩️ Назад":
        await start(update, context)
        return ConversationHandler.END
    
    token = update.message.text
    VK_TOKENS.append(token)
    await update.message.reply_text("Токен добавлен!")
    return ConversationHandler.END

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            ADDING_VK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_vk_token)],
            CHOOSING_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_account)],
            CHOOSING_USER_FOR_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_action)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == "__main__":
    main()
