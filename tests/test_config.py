"""Offline checks for safe and reproducible configuration."""

import os
import sys
from unittest.mock import patch

import pytest

from tft_simulator.config import DatabaseSettings, load_settings


def test_python_version():
    # 精确版本测试防止终端误用系统默认的另一套 Python。
    assert sys.version_info[:3] == (3, 13, 16)


def test_environment_overrides_dotenv(tmp_path):
    # 临时配置仅使用虚构测试值，验证外部环境变量具有优先权。
    env_file = tmp_path / ".env"
    env_file.write_text("DB_HOST=file-host\nDB_PASSWORD=test-placeholder\n", encoding="utf-8")
    # dotenv会自行写入环境变量；隔离整个映射，确保测试结束后新增键也被恢复。
    before = dict(os.environ)
    with patch.dict(os.environ):
        for key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_CONNECT_TIMEOUT"):
            os.environ.pop(key, None)
        os.environ["DB_HOST"] = "environment-host"
        settings = load_settings(env_file)
    assert dict(os.environ) == before
    assert settings.host == "environment-host"
    assert settings.password == "test-placeholder"
    assert "test-placeholder" not in repr(settings)
    assert settings.connection_kwargs()["port"] == 5432


@pytest.mark.parametrize("port", [0, 65536])
def test_invalid_port(port):
    # 边界配置应在建立连接前给出错误。
    with pytest.raises(ValueError):
        DatabaseSettings(port=port)


@pytest.mark.parametrize("timeout", [0, 61])
def test_invalid_timeout(timeout):
    # 有限超时保证数据库不可达时检查程序能够及时退出。
    with pytest.raises(ValueError):
        DatabaseSettings(connect_timeout=timeout)
