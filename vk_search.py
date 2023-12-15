import asyncio
import json
import aiohttp
from db import Database
from settings.tokens import TOKENS
from aiohttp.client_exceptions import ClientError


class Parser():

    def __init__(self):
        self.users_counter = 1  # ID пользователя с которого начинаем поиск
        self.requests_counter = 1  # Счетчик кол-ва выполненных запросов
        self.ended = 850_000_000  # ID пользователя на котором заканчиваем поиск
        self.offset = 50  # Шаг пользователей для запроса
        self.errors = 0  # Кол-во ошибок за выполнение скрипта
        self.users_recorded = 0
        self.tokens = list(TOKENS)
        # self.tokens = [TOKEN_1]

    def logging_parser(self) -> None:
        """
        Запись последнего ID.
        """
        with open("logs/last_id.txt", "w+", encoding="utf-8") as file:
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

    async def send_request_on_api(self, session, url):
        """
        Отправляем запрос на vk api по сбилженой ссылке
        """
        response = await session.get(url)
        try:
            if response.status == 200:
                data = await response.json()
                if data.get('error'):
                    with open('logs/failed_request.txt', 'a', encoding='utf-8') as file:
                        file.write(f'{url}\n')
                return data
        except ClientError as e:
            self.increase_errors()
            with open('logs/errors.txt', 'a', encoding='utf-8') as file:
                file.write(f'{e}\n')

    def build_api(self):
        """
            Создаем API запросы для execute method
        """
        result_api = ''

        for _ in range(25):
            start_id = self.users_counter
            ids = ','.join([str(id) for id in range(start_id, start_id + self.offset + 1)])

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

    def check_users_data(self, data):

        for i in data:
            print(i)
            # with open('tests/result_data.json', 'a', encoding='utf-8') as file:
            #     file.write(json.dumps(i, indent=4, ensure_ascii=False))

    def writing_data_to_database(self, data):
        pass

    async def parse(self):
        counter = 1

        # while self.users_counter <= self.ended and self.errors <= 100:
        while counter <= 2:
            urls_lists = []
            for token in self.tokens:
                urls = [self.build_final_url(token) for _ in range(5)]  # Создаем 5 урлов для одного токена
                urls_lists.append(urls)

            session = aiohttp.ClientSession()
            for urls in urls_lists:
                response = await asyncio.gather(*[self.send_request_on_api(session, url) for url in urls],
                                                return_exceptions=True)

                self.check_users_data(response)
            await session.close()
            counter += 1


async def main():
    db = Database()
    db.create_table()
    parser = Parser()
    await parser.parse()


if __name__ == '__main__':
    asyncio.run(main())
