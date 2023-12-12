import sqlite3
import os


class Database(object):
    """Класс базы данных sqlite3"""

    current_file = os.path.realpath(__file__)
    DB_LOCATION = f"{os.path.dirname(current_file)}/db/Users_data.db"

    def __init__(self):
        """Инициализация DB"""
        self.connection = sqlite3.connect(Database.DB_LOCATION)
        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cursor.close()
        if isinstance(exc_value, Exception):
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()

    def close(self):
        """закрыть соединение sqlite3"""
        self.connection.close()

    def execute(self, new_data):
        """выполнить строку данных для текущего курсора"""
        self.cursor.execute(new_data)

    def executemany(self, many_new_data):
        """Добавить несколько данных в БД"""
        self.create_table()
        self.cursor.executemany("REPLACE INTO jobs VALUES(?, ?, ?, ?)", many_new_data)

    def create_table(self):
        """Создать таблицу базы данных, если она еще не существует"""
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS KirovUsers(
                vk_id INTEGER NOT NULL UNIQUE,
                sex INTEGER
            )"""
        )

    def commit(self):
        """Зафиксировать изменения в базе данных"""
        self.connection.commit()