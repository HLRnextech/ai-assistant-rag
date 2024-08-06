import psycopg2
from envs import DB_HOST, DATABASE_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME
import pandas.io.sql as sqlio


class DB:
    def __init__(self) -> None:
        self.connection = psycopg2.connect(
            database=DATABASE_NAME, user=DB_USERNAME,
            password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        self.connection.autocommit = False

    def query(self, query: str):
        data = sqlio.read_sql_query(query, self.connection)
        data = data.reset_index(drop=True)
        return data

    def execute(self, query: str):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            self.connection.commit()
        finally:
            cursor.close()


db = DB()
