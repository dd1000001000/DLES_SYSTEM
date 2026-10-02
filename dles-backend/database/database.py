import os
import queue

import pymysql

from logs.log import error_log, info_log
from utils.read_config.read_config import get_env, read_config

config = read_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))

# 连接池里最多保留多少条空闲连接；高峰期不够用时会临时多建连接，用完超出的直接关闭
MAX_IDLE_CONNECTIONS = 10


class ConnectionPool:
    def __init__(self, max_idle: int = MAX_IDLE_CONNECTIONS):
        self._idle = queue.LifoQueue(maxsize=max_idle)

    @staticmethod
    def _new_connection():
        return pymysql.connect(
            host=config.get('host', '127.0.0.1'),
            port=config.get('port', 3306),
            user=config['username'],
            password=get_env('DLES_DB_PASSWORD'),
            database=config['database_name'],
            charset='utf8mb4',
            connect_timeout=5,
            # 自动提交：连接复用时，查询不会一直停留在旧的事务快照里读到过期数据
            autocommit=True,
        )

    def acquire(self):
        while True:
            try:
                connection = self._idle.get_nowait()
            except queue.Empty:
                return self._new_connection()
            try:
                # 空闲连接可能已经被 MySQL 服务器超时断开，ping 一下并按需重连
                connection.ping(reconnect=True)
                return connection
            except pymysql.MySQLError:
                self.discard(connection)

    def release(self, connection):
        try:
            self._idle.put_nowait(connection)
        except queue.Full:
            self.discard(connection)

    @staticmethod
    def discard(connection):
        try:
            connection.close()
        except Exception:
            pass


pool = ConnectionPool()


class Database:
    """从连接池里借一条连接，close() 时归还。推荐用 with Database() as db: 保证异常时也会归还。"""

    def __init__(self):
        self.connection = None
        self._broken = False
        try:
            self.connection = pool.acquire()
        except pymysql.MySQLError as e:
            error_log(f'连接数据库失败: {e}')
            raise RuntimeError('数据库连接尚未建立') from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        # 兜底：调用方忘了 close 时，对象被回收的时候把连接还回去
        try:
            self.close()
        except Exception:
            pass

    def _run(self, sql, params):
        if self.connection is None:
            error_log(f'连接已经关闭: {sql}')
            raise RuntimeError('数据库连接已经关闭')
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            return cursor
        except pymysql.MySQLError:
            # 出错的连接状态不确定，不再放回池里复用
            self._broken = True
            raise

    def execute_query(self, query, params=None) -> list:
        cursor = self._run(query, params)
        try:
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def execute_update(self, update, params=None):
        cursor = self._run(update, params)
        cursor.close()
        info_log(f'数据库修改成功: {update}')

    def close(self):
        connection, self.connection = self.connection, None
        if connection is None:
            return
        if self._broken:
            pool.discard(connection)
        else:
            pool.release(connection)
