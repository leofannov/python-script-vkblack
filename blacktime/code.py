import requests
import time
import json
from datetime import datetime

class VKBanManager:
    def __init__(self):
        self.tokens_file = "tokens.json"
        self.blacklist_file = "blacklist.txt"
        self.load_config()

    def load_config(self):
        try:
            with open(self.tokens_file, 'r') as f:
                self.tokens = json.load(f)
        except FileNotFoundError:
            self.tokens = []
        
        try:
            with open(self.blacklist_file, 'r') as f:
                self.blacklist = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.blacklist = []

    def save_tokens(self):
        with open(self.tokens_file, 'w') as f:
            json.dump(self.tokens, f, indent=4)

    def add_token(self, new_token):
        if new_token not in self.tokens:
            self.tokens.append(new_token)
            self.save_tokens()
            return True
        return False

    def get_user_info(self, token, user_id):
        """Получает информацию о пользователе по ID"""
        url = "https://api.vk.ru/method/users.get"
        params = {
            "access_token": token,
            "v": "5.131",
            "user_ids": user_id,
            "fields": "first_name,last_name"
        }
        try:
            response = requests.post(url, params=params)
            data = response.json()
            if 'response' in data and len(data['response']) > 0:
                user = data['response'][0]
                return f"{user['first_name']} {user['last_name']} (ID: {user_id})"
        except Exception:
            pass
        return f"Неизвестный пользователь (ID: {user_id})"

    def ban_user(self, token, user_id):
        url = "https://api.vk.ru/method/account.ban"
        params = {
            "access_token": token,
            "v": "5.131",
            "owner_id": user_id
        }
        response = requests.post(url, params=params)
        return response.json()

    def unban_user(self, token, user_id):
        url = "https://api.vk.ru/method/account.unban"
        params = {
            "access_token": token,
            "v": "5.131",
            "owner_id": user_id
        }
        response = requests.post(url, params=params)
        return response.json()

    def process_blacklist(self, action):
        results = []
        for token in self.tokens:
            for user_id in self.blacklist:
                try:
                    if action == "ban":
                        result = self.ban_user(token, user_id)
                    else:
                        result = self.unban_user(token, user_id)
                    
                    # Получаем информацию о пользователе для красивого вывода
                    user_info = self.get_user_info(token, user_id)
                    
                    results.append({
                        "token": token[:10] + "...",
                        "user_id": user_id,
                        "user_info": user_info,
                        "result": result
                    })
                    
                    time.sleep(0.3)  # Задержка между запросами
                    
                except Exception as e:
                    # Все равно пытаемся получить информацию о пользователе даже при ошибке
                    user_info = self.get_user_info(token, user_id)
                    results.append({
                        "token": token[:10] + "...",
                        "user_id": user_id,
                        "user_info": user_info,
                        "error": str(e)
                    })
        return results

def main():
    manager = VKBanManager()
    
    while True:
        command = input("Введите команду (/ban, /unban, /add_token, /exit): ").strip().lower()
        
        if command == "/exit":
            break
            
        elif command == "/add_token":
            token = input("Введите новый токен: ").strip()
            if manager.add_token(token):
                print("Токен успешно добавлен!")
            else:
                print("Токен уже существует!")
                
        elif command in ["/ban", "/unban"]:
            action = "ban" if command == "/ban" else "unban"
            action_text = "забанен" if action == "ban" else "разбанен"
            
            print(f"\nНачинаю процесс {action_text}...")
            results = manager.process_blacklist(action)
            
            print(f"\nРезультаты операции:")
            print("-" * 50)
            
            for result in results:
                if 'error' in result:
                    print(f"❌ Ошибка для {result['user_info']}: {result['error']}")
                else:
                    if 'response' in result['result'] and result['result']['response'] == 1:
                        print(f"✅ Успешно {action_text}: {result['user_info']} (токен: {result['token']})")
                    else:
                        error_msg = result['result'].get('error', {}).get('error_msg', 'Неизвестная ошибка')
                        print(f"⚠️  Ошибка для {result['user_info']}: {error_msg}")
            
            print("-" * 50)
            print(f"Обработано пользователей: {len(results)}")
                    
        else:
            print("Неизвестная команда")

if __name__ == "__main__":
    main()
