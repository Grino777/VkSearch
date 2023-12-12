#!/usr/bin/python3

import json
import asyncio
from db import Database
import vk
from asyncio import Task

from settings import TOKEN_1, TOKEN_2, TOKEN_3, TOKEN_4, TOKEN_5, TOKEN_6, TOKEN_7, TOKEN_8, TOKEN_9, TOKEN_10


class VkParser:
    SEARCH_CITY_ID = 66

    def __init__(self) -> None:
        self.users_counter = 1  # ID пользователя с которого начинаем поиск
        self.requests_counter = 1  # Счетчик кол-ва выполненных запросов
        self.ended = 850_000_000  # ID пользователя на котором заканчиваем поиск
        self.offset = 1000  # Шаг пользователей для запроса
        self.errors = 0
        self.tokens = [TOKEN_1, TOKEN_2, TOKEN_3, TOKEN_4, TOKEN_5, TOKEN_6, TOKEN_7, TOKEN_8, TOKEN_9, TOKEN_10]

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

    def logging_parser(self) -> None:
        """
        Запись последнего ID.
        """
        with open("logs/last_id.txt", "w+", encoding="utf-8") as file:
            file.write(str(self.users_counter))

    async def send_request_on_api(self, users, token):
        """
        Отправляем запрос на vk api по сбилженой ссылке
        """
        print("Запрос отправлен! Ожидаем...")

        api = vk.API(access_token=token, v="5.131")

        return api.users.get(user_ids=f"{users}", fields='city,sex')

    def generate_users_ids(self) -> str:
        """
        Генерируем (offset) айдишников для отдельного подзапроса.
        """

        start_user_id = self.users_counter

        users = [str(i) for i in range(start_user_id, start_user_id + self.offset)]
        self.increase_users_counter()
        users = ",".join(users)
        return users

    def check_users(self, result: Task):
        """
        Проверем пользователя на "deactivated" и city_id
        Если в execute-запросе все пользователи deactivated, то заканчиваем парсинг
        """
        self.increase_requests_counter()

        if result.exception():
            self.increase_errors()
            with open('logs/errors.txt', 'a', encoding='utf-8') as file:
                message = result.exception().message
                params = result.exception().request_params

                file.write(f'{message}, {params}\n')
        else:
            result_data = []

            for item in result.result():
                if "deactivated" not in item.keys():
                    city = item.get("city", False)
                    user_id = item.get("id")
                    sex = item.get("sex", False)
                    if city == self.SEARCH_CITY_ID:
                        result_data.append({"id": user_id, "city": city, "sex": sex})

            if result_data:
                self.writing_data_to_database(result)
            else:
                print("Данных нет!\n", "-" * 40)

    def writing_data_to_database(self, data):
        """
        Запись данных из запроса в БД
        """
        print("Началась запись в БД")
        with Database() as database:
            for user in data:
                database.cursor.execute("INSERT INTO KirovUsers (vk_id, sex) VALUES (?)", (user.get("id"), user.get("sex")))
        print("Данные записаны\n", "-" * 40)

    async def parse(self):

        while (self.users_counter <= self.ended) and (self.errors <= 100):
            done, _ = await asyncio.wait(
                [self.send_request_on_api(self.generate_users_ids(), token) for token in self.tokens])
            for response in done:
                self.check_users(response)

            self.logging_parser()

            print(f'Запросов выполнено: {self.requests_counter}\n')
            print(f'Пользователей обработано: {self.users_counter}')

            await asyncio.sleep(1)
            break


if __name__ == "__main__":
    db = Database()
    db.create_table()
    parser = VkParser()
    asyncio.run(parser.parse())
