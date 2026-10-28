"""Shared lifecycle for read-only and maintenance connections."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

import psycopg

from tft_simulator.config import load_settings


@contextmanager
def _connection(*, read_only: bool) -> Iterator[psycopg.Connection]:
    # 统一读取配置、核对数据库和关闭连接，避免查询与写入模块重复实现。
    with psycopg.connect(**load_settings().connection_kwargs()) as connection:
        connection.read_only = read_only
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != "tft_balance_simulator":
                raise ValueError("Expected database tft_balance_simulator")
        yield connection
        # with正常退出时提交；发生异常时回滚。函数不吞掉异常。


def read_connection() -> AbstractContextManager[psycopg.Connection]:
    # 普通读取继续使用只读事务，已有Notebook导入方式保持兼容。
    return _connection(read_only=True)


def write_connection() -> AbstractContextManager[psycopg.Connection]:
    # 显式维护入口；修改源数据必须有相应授权，不用于数值实验。
    return _connection(read_only=False)
