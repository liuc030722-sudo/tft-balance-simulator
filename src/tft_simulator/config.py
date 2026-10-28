"""Environment-based database configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    # 避免在对象日志中显示密码；连接参数独立传递，无需拼接含密码的 URL。
    host: str = "localhost"
    port: int = 5432
    dbname: str = "tft_balance_simulator"
    user: str = "postgres"
    password: str = field(default="", repr=False)
    connect_timeout: int = 5

    def __post_init__(self) -> None:
        # 提前拒绝非法端口和无界等待，避免配置错误直到连接时才暴露。
        if not 1 <= self.port <= 65535:
            raise ValueError("DB_PORT must be between 1 and 65535")
        if not 1 <= self.connect_timeout <= 60:
            raise ValueError("DB_CONNECT_TIMEOUT must be between 1 and 60")

    def connection_kwargs(self) -> dict[str, str | int]:
        # 使用 psycopg 参数接口，不将密码写入诊断输出。
        return {
            "host": self.host, "port": self.port, "dbname": self.dbname,
            "user": self.user, "password": self.password,
            "connect_timeout": self.connect_timeout,
        }


def load_settings(env_file: Path | None = None) -> DatabaseSettings:
    # 按项目位置加载 .env，不依赖终端工作目录；已有环境变量具有更高优先级。
    if env_file is None:
        env_file = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_file, override=False)
    return DatabaseSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "tft_balance_simulator"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
    )
