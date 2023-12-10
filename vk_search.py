#!/venv/bin/python3

from time import sleep
from requests import ConnectionError
import requests
from fake_headers import Headers
from settings import TOKEN
import json
import asyncio
from db import Database


class VkParser:
    SEARCH_CITY_ID = 66

    def __init__(self):
        self.users_counter = 1
        self.ended = False
        self.offset = 50
        self.response_status = None
        self.temp_counter = self.users_counter

    def increase_counter(self):
        """
        Увеличиваем значение счетчика на offset.
        """
        self.temp_counter += self.offset

    def generate_users_ids(self):
        """
        Генерируем offset айдишников для создания отдельного метода запроса.
        """

        user_id = self.temp_counter

        users = [str(i) for i in range(user_id, user_id + self.offset)]
        self.increase_counter()
        users = ",".join(users)
        return users

    def build_url(self):
        """
        Собираем итоговый запрос из 25 подзапросов
        """

        token = TOKEN
        methods = ""

        for _ in range(25):
            users = self.generate_users_ids()
            api = f"API.users.get({{'user_ids':'{users}','fields':'city'}}),"
            methods += api

        url = f"https://api.vk.com/method/execute?access_token={token}&v=5.81&code=return [{methods}];"

        # with open("json_tests/url.txt", "a", encoding="utf-8") as file:
        #     file.write(f"{url}\n")

        return url

    async def send_request_on_api(self, url):
        """
        Отправляем запрос на vk api по сбилженой ссылке
        """
        print("Запрос отправлен! Ожидаем...")

        my_header = Headers(
            browser="chrome",  # Generate only Chrome UA
            os="win",  # Generate ony Windows platform
            headers=True,  # generate misc headers
        )

        headers = my_header.generate()

        try:
            response = requests.post(url, headers=headers, timeout=10)
            self.response_status = response.status_code

            if self.response_status == 200:
                print(f"Запрос выполнен успешно: {self.response_status}")
                data = json.loads(response.text)
                return data
            else:
                self.response_status = response.status_code
                print(f"Запрос выполнен с статусом: {self.response_status}")
        except ConnectionError as e:
            print(e)
            return False

    def logging_parser(self):
        """
        Запись последнего ID
        """
        with open("logs/last_id.txt", "w+", encoding="utf-8") as file:
            file.write(str(self.users_counter))

    def check_users(self, users_data: dict):
        """
        Проверем пользователя на "deactivated" и city_id
        Если в execute-запросе все пользователи deactivated, то заканчиваем парсинг
        """
        result_data = []

        for items in users_data:
            for item in items:
                if "deactivated" not in item.keys():
                    city = item.get("city", False)
                    user_id = item.get("id")
                    city = city.get("id") if city else None
                    result_data.append({"id": user_id, "city": city})

        if result_data:
            result = [user for user in result_data if user.get("city") == self.SEARCH_CITY_ID]
            self.writing_data_to_database(result)
        else:
            self.ended = True

    def writing_data_to_database(self, data):
        """
        Запись данных из запроса в БД
        """
        print("Началась запись в БД")
        with Database() as database:
            for user in data:
                database.cursor.execute("INSERT INTO KirovUsers (vk_id) VALUES (?)", (user.get("id"),))
        print("Данные записаны\n", "-" * 40)

    async def parse(self):
        requests_counter = 0
        url = ""

        while self.ended:  #!self.ended
            print(f"#Запрос №{requests_counter}")
            url = self.build_url()

            # data = await asyncio.create_task(self.send_request_on_api(url=url))
            data = await self.send_request_on_api(url=url)
            if self.response_status == 200:
                try:
                    if data:
                        self.check_users(data.get("response"))
                        # with open("json_tests/vk.json", "w", encoding="utf-8") as file:
                        #     file.write(json.dumps(data.get("response"), indent=4, ensure_ascii=False))
                        self.users_counter = self.temp_counter
                    else:
                        with open("logs/errors.txt", "a+", encoding="utf-8") as file:
                            file.write(f"Данные пользователей {self.temp_counter}-{self.users_counter} не записаны\n")
                        self.temp_counter = self.users_counter
                except Exception as e:
                    with open("logs/exeptions.txt", "a+", encoding="utf-8") as file:
                        file.write(f"{self.temp_counter}-{self.users_counter}: {e}\n")

            if self.response_status == 200:
                requests_counter += 1
            else:
                sleep(3)

            if requests_counter % 5:
                sleep(5)

        self.logging_parser()


if __name__ == "__main__":
    db = Database()
    db.create_table()
    parser = VkParser()
    asyncio.run(parser.parse())
