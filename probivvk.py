import vk_api
import json

class VKUserInfoBot:
    def __init__(self, user_token):
        # Инициализируем сессию с токеном пользователя
        self.vk_session = vk_api.VkApi(token=user_token)
        self.vk = self.vk_session.get_api()
    
    def get_user_info(self, user_id):
        """
        Получает расширенную информацию о пользователе VK
        """
        try:
            # Получаем информацию о пользователе
            user_info = self.vk.users.get(
                user_ids=user_id,
                fields='first_name,last_name,bdate,sex,city,country,photo_max_orig,' +
                       'education,universities,schools,career,activities,interests,' +
                       'music,movies,tv,books,games,about,quotes,contacts,relation,' +
                       'home_town,domain,site,status,last_seen,online,counters'
            )
            
            if not user_info:
                return "Пользователь не найден или информация скрыта настройками приватности"
                
            user_info = user_info[0]
            
            return self.format_user_info(user_info)
            
        except Exception as e:
            return f"Ошибка при получении информации: {e}"
    
    def format_user_info(self, user_info):
        """
        Форматирует информацию о пользователе в читаемый вид
        """
        # Проверяем, есть ли основные поля
        if 'first_name' not in user_info:
            return "Не удалось получить основную информацию о пользователе. Возможно, профиль закрыт."
        
        # Основная информация
        result = f"""
👤 ОСНОВНАЯ ИНФОРМАЦИЯ:
• ID: {user_info.get('id', 'Неизвестно')}
• Имя: {user_info.get('first_name', 'Не указано')}
• Фамилия: {user_info.get('last_name', 'Не указано')}
• Полное имя: {user_info.get('first_name', '')} {user_info.get('last_name', '')}
• Дата рождения: {user_info.get('bdate', 'Не указана')}
• Пол: {self.get_sex(user_info.get('sex'))}
• Семейное положение: {self.get_relation(user_info.get('relation'))}
• Город: {self.get_city_name(user_info)}
• Страна: {self.get_country_name(user_info)}
• Родной город: {user_info.get('home_town', 'Не указан')}
• Статус: {user_info.get('status', 'Не указан')}
• Сайт: {user_info.get('site', 'Не указан')}
• Последний визит: {self.get_last_seen(user_info)}
• Онлайн: {'Да' if user_info.get('online') else 'Нет'}
"""
        
        # Счетчики (друзья, подписчики и т.д.)
        counters = user_info.get('counters', {})
        if counters:
            result += f"""
📊 СТАТИСТИКА:
• Друзей: {counters.get('friends', 0)}
• Подписчиков: {counters.get('followers', 0)}
• Фотографий: {counters.get('photos', 0)}
• Видеозаписей: {counters.get('videos', 0)}
• Аудиозаписей: {counters.get('audios', 0)}
• Групп: {counters.get('groups', 0)}
"""
        
        # Образование
        education_info = self.get_education_info(user_info)
        result += f"\n🎓 ОБРАЗОВАНИЕ:\n{education_info}"
        
        # Карьера
        career_info = self.get_career_info(user_info)
        result += f"\n💼 КАРЬЕРА:\n{career_info}"
        
        # Интересы
        interests_info = self.get_interests_info(user_info)
        result += f"\n🎭 ИНТЕРЕСЫ И УВЛЕЧЕНИЯ:\n{interests_info}"
        
        # Контакты
        contacts_info = self.get_contacts_info(user_info)
        result += f"\n📞 КОНТАКТЫ:\n{contacts_info}"
        
        # Ссылки
        domain = user_info.get('domain', f"id{user_info['id']}")
        result += f"""
🔗 ССЫЛКИ:
• Фото: {user_info.get('photo_max_orig', 'Не доступно')}
• Профиль: https://vk.ru/{domain}
"""
        
        return result
    
    def get_sex(self, sex_code):
        sex_map = {1: 'Женский', 2: 'Мужской', 0: 'Не указан'}
        return sex_map.get(sex_code, 'Не указан')
    
    def get_relation(self, relation_code):
        relation_map = {
            1: 'Не женат/Не замужем',
            2: 'Есть друг/Есть подруга',
            3: 'Помолвлен/Помолвлена',
            4: 'Женат/Замужем',
            5: 'Всё сложно',
            6: 'В активном поиске',
            7: 'Влюблён/Влюблена',
            8: 'В гражданском браке',
            0: 'Не указано'
        }
        return relation_map.get(relation_code, 'Не указано')
    
    def get_last_seen(self, user_info):
        if 'last_seen' in user_info:
            from datetime import datetime
            timestamp = user_info['last_seen']['time']
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return 'Неизвестно'
    
    def get_city_name(self, user_info):
        if 'city' in user_info and isinstance(user_info['city'], dict):
            return user_info['city'].get('title', 'Не указан')
        return 'Не указаn'
    
    def get_country_name(self, user_info):
        if 'country' in user_info and isinstance(user_info['country'], dict):
            return user_info['country'].get('title', 'Не указан')
        return 'Не указан'
    
    def get_education_info(self, user_info):
        info = []
        
        # Высшее образование
        if 'universities' in user_info and user_info['universities']:
            for uni in user_info['universities']:
                uni_info = f"• {uni.get('name', 'Неизвестно')}"
                if uni.get('faculty_name'):
                    uni_info += f", {uni['faculty_name']}"
                if uni.get('graduation'):
                    uni_info += f" (выпуск {uni['graduation']})"
                info.append(uni_info)
        
        # Школы
        if 'schools' in user_info and user_info['schools']:
            for school in user_info['schools']:
                school_info = f"• {school.get('name', 'Неизвестно')}"
                if school.get('year_graduation'):
                    school_info += f" (выпуск {school['year_graduation']})"
                if school.get('year_from'):
                    school_info += f", с {school['year_from']}"
                info.append(school_info)
        
        # Общее образование
        if user_info.get('education_form'):
            info.append(f"• Форма обучения: {user_info['education_form']}")
        if user_info.get('education_status'):
            info.append(f"• Статус: {user_info['education_status']}")
        
        return "\n".join(info) if info else "• Не указано"
    
    def get_career_info(self, user_info):
        info = []
        
        if 'career' in user_info and user_info['career']:
            for job in user_info['career']:
                job_info = f"• {job.get('company', 'Неизвестно')}"
                if job.get('position'):
                    job_info += f", {job['position']}"
                if job.get('city_name'):
                    job_info += f" ({job['city_name']})"
                if job.get('year_from'):
                    job_info += f", с {job['year_from']}"
                info.append(job_info)
        
        return "\n".join(info) if info else "• Не указано"
    
    def get_interests_info(self, user_info):
        info = []
        
        interests_map = {
            'activities': 'Деятельность',
            'interests': 'Интересы',
            'music': 'Музыка',
            'movies': 'Фильмы',
            'tv': 'ТВ передачи',
            'books': 'Книги',
            'games': 'Игры',
            'quotes': 'Цитаты',
            'about': 'О себе'
        }
        
        for field, title in interests_map.items():
            if user_info.get(field):
                content = user_info[field]
                # Обрезаем слишком длинные тексты
                if len(content) > 200:
                    content = content[:200] + "..."
                info.append(f"• {title}: {content}")
        
        return "\n".join(info) if info else "• Не указано"
    
    def get_contacts_info(self, user_info):
        info = []
        
        contacts_map = {
            'mobile_phone': 'Мобильный телефон',
            'home_phone': 'Домашний телефон',
            'skype': 'Skype',
            'facebook': 'Facebook',
            'twitter': 'Twitter',
            'instagram': 'Instagram'
        }
        
        for field, title in contacts_map.items():
            if user_info.get(field):
                info.append(f"• {title}: {user_info[field]}")
        
        return "\n".join(info) if info else "• Не указано"
    
    def run_console_mode(self):
        """
        Запускает бота в консольном режиме
        """
        print("VK Info Bot запущен в консольном режиме")
        print("Введите ID пользователя или 'выход' для завершения")
        print("Примеры: id1, durov, 123456789")
        
        while True:
            user_input = input("\nВведите ID пользователя: ").strip()
            
            if user_input.lower() in ['выход', 'exit', 'quit']:
                print("Завершение работы...")
                break
                
            if not user_input:
                continue
                
            print("\n" + "="*80)
            print(self.get_user_info(user_input))
            print("="*80)

# Ваш токен VK (замените на свой)
USER_TOKEN = "token"

# Основная функция
if __name__ == "__main__":
    print("VK User Info Bot")
    print("=" * 50)
    
    if USER_TOKEN and USER_TOKEN != "ваш_токен_здесь":
        try:
            bot = VKUserInfoBot(USER_TOKEN)
            bot.run_console_mode()
        except Exception as e:
            print(f"Ошибка при инициализации бота: {e}")
            print("Проверьте правильность токена доступа")
    else:
        print("ОШИБКА: Токен не указан!")
        print("Пожалуйста, замените 'ваш_токен_здесь' на ваш действительный токен VK")
        print("\nКак получить токен:")
        print("1. Перейдите по ссылке: https://oauth.vk.com/authorize?client_id=6121396&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=friends,photos,status,offline&response_type=token&v=5.131")
        print("2. Разрешите доступ приложению")
        print("3. Скопируйте token из адресной строки (часть между access_token= и &expires_in)")
        print("4. Вставьте токен в переменную USER_TOKEN")
