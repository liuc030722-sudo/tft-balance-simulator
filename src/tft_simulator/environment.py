"""Read-only Python and PostgreSQL environment checks."""

import sys

import psycopg

from tft_simulator.config import load_settings


def main() -> int:
    # 所有数据库操作仅查询；只有成功连接目标库才算验收通过。
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info[:3] != (3, 13, 16):
        print("FAIL: this project expects Python 3.13.16")
        return 1
    try:
        settings = load_settings()
    except ValueError:
        print("FAIL: invalid database configuration; check .env")
        return 1
    for database in (settings.dbname, "postgres"):
        parameters = settings.connection_kwargs()
        parameters["dbname"] = database
        try:
            with psycopg.connect(**parameters) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_database(), current_setting('server_version')")
                    name, version = cursor.fetchone()
                    if database == settings.dbname:
                        print(f"PASS: connected to {name}; PostgreSQL {version}")
                        return 0
                    # 目标库连接失败时，只在维护库中查询是否存在，不创建或更改数据库。
                    cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = %s)", (settings.dbname,))
                    exists = cursor.fetchone()[0]
                    print(f"Target database exists: {exists}")
                    if not exists:
                        print("Run sql/create_database.sql in DBeaver, then retry.")
        except psycopg.Error as error:
            # 仅打印异常类型与 SQLSTATE，避免连接错误文本泄露密码或本地路径。
            print(f"FAIL: {database}: {type(error).__name__}; SQLSTATE={error.sqlstate or 'unavailable'}")
    print("Database check incomplete. Verify local .env credentials and PostgreSQL access.")
    return 1


if __name__ == "__main__":
    # 模块执行和安装后的 tft-check 命令共享同一检查入口。
    raise SystemExit(main())
