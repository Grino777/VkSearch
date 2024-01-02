import psycopg2
from psycopg2.errors import DuplicateDatabase

from settings.settings import DB_LOGIN, DB_PASSWORD


class Database():
    """Класс базы данных postgres database"""

    def __init__(self):
        """Инициализация DB"""
        self.db_name = 'vk_users'  # Название таблицы в БД
        self._connect_db()

    def __enter__(self):
        return self.connection

    def __exit__(self, ext_type, exc_value, traceback):
        self.cursor.close()
        if isinstance(exc_value, Exception):
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()

    def _create_db(self):
        self.connection = psycopg2.connect(dbname='vk_users',
                                           user=DB_LOGIN,
                                           password=DB_PASSWORD,
                                           host='127.0.0.1',
                                           port='5432')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()
        try:
            self.cursor.execute(f'CREATE DATABASE {self.db_name}')
        except DuplicateDatabase:
            pass
        self.connection.close()

    def _connect_db(self):
        self._create_db()
        self.connection = psycopg2.connect(dbname=self.db_name,
                                           user=DB_LOGIN,
                                           password=DB_PASSWORD,
                                           host='127.0.0.1',
                                           port='5432')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

    def close(self):
        """Закрыть соединение"""
        self.connection.close()

    def commit(self):
        """Зафиксировать изменения в базе данных"""
        self.connection.commit()

    def drop_db(self):
        self.cursor.execute(f'DROP DATABASE IF EXISTS {self.db_name}')

    def create_table(self, table_name='KirovUsers'):
        """
            Создаем таблицу в БД
        """
        self.cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} (vk_id INTEGER NOT NULL UNIQUE, sex VARCHAR(50))"
        )
