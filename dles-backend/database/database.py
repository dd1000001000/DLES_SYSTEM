import os

import pymysql

from logs.log import error_log, info_log
from utils.read_config.read_config import read_config

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))


class Database:
    def __init__(self):
        self.host = '127.0.0.1'
        self.user = config['username']
        self.password = config['password']
        self.database = config['database_name']
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor()
        except pymysql.MySQLError as e:
            error_log(f'连接数据库失败: {e}')
            self.connection = None
            self.cursor = None

    def execute_query(self, query) -> list:
        if self.cursor:
            self.cursor.execute(query)
            columns = [column[0] for column in self.cursor.description]
            results = self.cursor.fetchall()
            dict_list = [dict(zip(columns, row)) for row in results]
            return dict_list
        else:
            error_log(f'连接尚未建立: {query}')
            return None

    def execute_update(self, update):
        if self.cursor:
            self.cursor.execute(update)
            self.connection.commit()
            info_log(f'数据库修改成功: {update}')
        else:
            error_log(f'数据库修改失败: {update}')

    def close(self):
        if self.connection:
            self.cursor.close()
            self.connection.close()

# db = Database()
# sql = 'SELECT * FROM user'
# res = db.execute_query(sql)
# print(res)
