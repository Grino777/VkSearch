import asyncio
import json
from sqlite3 import IntegrityError
from time import gmtime, strftime, time
import aiohttp
from db import Database
from settings.tokens import TOKENS
from validator.user_validator import User
import os


class Parser():

    def __init__(self):
        self.users_counter = 1  # ID пользователя с которого начинаем поиск
        self.requests_counter = 1  # Счетчик кол-ва выполненных запросов
        self.ended = 850_000_000  # ID пользователя на котором заканчиваем поиск
        self.offset = 50  # Шаг пользователей для запроса
        self.errors = 0  # Кол-во ошибок за выполнение скрипта
        self.users_recorded = 0
        self.tokens = TOKENS
        self.requests_completed = 0
        self.requests_limit = 20
        self.requests_with_error = 0
        # self.tokens = [TOKEN_1]

    def logging_parser(self) -> None:
        """
            Запись последнего ID.
        """
        with open("logs/last_id.txt", "w", encoding="utf-8") as file:
            file.write(str(self.users_counter))

    def increase_errors(self):
        self.errors = +1

    def increase_requests_counter(self) -> None:
        """
            Увеличиваем значение счетчика запросов на 1.
        """
        self.requests_counter += 1

    def increase_users_counter(self) -> None:
        """
            Увеличиваем значение счетчика пользователей на offset.
        """
        self.users_counter += self.offset

    def build_api(self):
        """
            Создаем API запросы для execute method
        """
        result_api = ''

        for _ in range(25):
            start_id = self.users_counter
            ids = ','.join([str(id) for id in range(start_id, start_id + self.offset)])

            result_api += f"API.users.get({{'user_ids':'{ids}','fields':'city,sex'}}),"
            self.increase_users_counter()

        return result_api

    def build_final_url(self, token):
        """
            Билдим url для дальнейшего запроса на api.
        """

        result_api = self.build_api()
        url = f"https://api.vk.com/method/execute?access_token={token}&v=5.199&code=return [{result_api}];"

        return url

    def get_validate_list(self, data):
        result = []
        for users in data:
            for user in users:
                user = {
                    "id": user.get('id'),
                    "sex": user.get('sex'),
                    "city": user.get('city', False),
                    "deactivated": user.get('deactivated', False)
                }
                if user.get('deactivated'):
                    continue
                try:
                    result.append(User(**user))
                except ValueError:
                    continue
        return result

    def writing_data_to_database(self, data):
        users = 0

        with Database() as database:
            for user in data:
                try:
                    database.cursor.execute("INSERT INTO KirovUsers (vk_id, sex) VALUES (?, ?)", (user.id, user.sex))
                    users += 1
                except IntegrityError:
                    continue
                except Exception as e:
                    print(f'Ошибка записи в БД! {e}')

        self.users_recorded += users

    def check_response(self, response_data):
        """
            Проверка данных всех ответов
        """
        if response_data:
            for data in response_data:
                try:
                    result = [user for user in data]
                    result = self.get_validate_list(result)
                    self.writing_data_to_database(result)
                    self.requests_completed += 1
                except TypeError:
                    continue

    async def send_requests_on_api(self, session, url):
        """
        Отправляем запрос на vk api по сбилженой ссылке
        """
        data = {}
        try:
            async with session.get(url) as response:
                data = str(await response.text()).replace("b\'", "").replace("]}'", ']}')
                data = fr'{data}'
                data = json.loads(data)

                if response.status == 200 and 'response' in data:
                    data = data.get('response')
                else:
                    error = None
                    if 'error' in data:
                        error = data.get('error').get('error_msg')
                        raise ValueError(f'{error}')
        except Exception as e:
            data = None
            self.requests_with_error += 1
            with open('logs/failed_request.txt', 'a', encoding='utf-8') as file:
                file.write(f'{url}\n')
            with open('logs/errors.txt', 'a', encoding='utf-8') as error_file:
                error_file.write(f"{e}\n")
        return data

    async def get_failed_requests(self):
        with open('logs/failed_request.txt', 'w+', encoding='utf-8') as file:
            urls = file.read().split('\n')
            old_urls = [url for url in urls if url.startswith('https:')]

        x = 10 - len(old_urls) % 10
        old_urls.extend(['' for _ in range(x)])
        chunk_size = 10
        new_list = [old_urls[i:i + chunk_size] for i in range(0, len(old_urls), chunk_size)]

        result = []

        for urls in new_list:
            async with aiohttp.ClientSession() as session:
                response = await asyncio.gather(*[self.send_requests_on_api(session, url) for url in urls if url])
                result.extend(response)
            await asyncio.sleep(0.5)

        self.check_response(result)

    async def parse(self):
        start = time()
        total_requests = len(self.tokens) * self.requests_limit

        while self.users_counter <= self.ended and self.errors <= 100:
            urls_list = []
            for token in self.tokens:
                urls = [(self.build_final_url(token)) for _ in range(self.requests_limit)]
                urls_list.extend(urls)
            async with aiohttp.ClientSession() as session:

                # Создаем n (self.requests_limit) урлов для одного токена
                response = await asyncio.gather(
                    *[self.send_requests_on_api(session=session, url=url) for url in urls_list])

            response = list(filter(None, response))

            self.check_response(response)

            self.logging_parser()

            failed_requests = total_requests - len(response)

            print("-" * 40)
            print(f"Запросов выполнено: {self.requests_completed:_}")
            print(f'Успешных запросов за цикл: {total_requests - failed_requests}/{total_requests}')
            print(f"Пользователей проверено: {self.users_counter:_}")
            print(f"Непроверенных пользователей: {(self.ended - self.users_counter):_}")
            print(f"Пользователей записано: {self.users_recorded:_}")
            print(f"Запросов с ошибкой: {self.requests_with_error}")
            print('Времент прошло: ', strftime('%H:%M:%S', gmtime(time() - start)))
            print("-" * 40)
            await asyncio.sleep(1)

        print('=' * 15, 'ПАРСИНГ ЗАВЕРШЕН', '=' * 15)


async def main():
    os.makedirs('db', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    db = Database()
    db.create_table()
    parser = Parser()
    await parser.parse()
    # await parser.get_failed_requests()


if __name__ == '__main__':
    asyncio.run(main())
