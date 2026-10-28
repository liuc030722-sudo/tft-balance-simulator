"""Opt-in read-only integration tests against the imported research snapshot."""

import os

import pytest

from tft_simulator.database.queries import (
    get_ability, get_champion, get_counts, list_champions, list_versions,
    read_connection,
)


@pytest.fixture(scope="module")
def database():
    # 默认离线测试不要求PostgreSQL；显式启用后必须连通并找到固定快照。
    if os.getenv("TFT_TEST_DATABASE") != "1":
        pytest.skip("Set TFT_TEST_DATABASE=1 to run local database integration tests")
    with read_connection() as connection:
        matches = [
            row for row in list_versions(connection)
            if row["set_number"] == 10 and row["patch"] == "14.1"
            and row["source_sha256"] ==
            "ae6d4bde7f591194b599caa120ca36ccc592bb5d9942ae703a47bd0cd0f7cb56"
        ]
        if len(matches) != 1:
            pytest.fail("Import the documented Set 10 / patch 14.1 snapshot first")
        yield connection, matches[0]["version_id"]


def test_imported_counts(database):
    # 验证真实数据库中的三类关联记录，而非仅验证模拟返回值。
    connection, version_id = database
    assert get_counts(connection, version_id) == {
        "versions": 1, "champions": 15, "abilities": 15,
    }


def test_cost_filter(database):
    # 二费筛选必须返回当前已导入样本中的三名英雄，顺序稳定。
    connection, version_id = database
    rows = list_champions(connection, version_id, cost=2)
    assert [row["champion_id"] for row in rows] == [
        "TFT10_Garen", "TFT10_Jax", "TFT10_Senna",
    ]
    assert all(row["cost"] == 2 and row["version_id"] == version_id for row in rows)


def test_types_and_source_values(database):
    # 检查PostgreSQL数组、JSONB与浮点值确实恢复成Python可用的数据。
    connection, version_id = database
    champion = get_champion(connection, version_id, "TFT10_Annie")
    ability = get_ability(connection, version_id, "TFT10_Annie")
    assert champion["hp"] == 450.0
    assert champion["traits"] == ["Emo", "Spellweaver"]
    assert ability["ability_name"] == "Disintegrate"
    assert isinstance(ability["variables"], list)
    magic_damage = next(v for v in ability["variables"] if v["name"] == "MagicDamage")
    assert magic_damage["value"] == [0.0, 220.0, 330.0, 495.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize("identifier", ["DOES_NOT_EXIST", "' OR '1'='1"])
def test_unknown_or_sql_like_id_returns_none(database, identifier):
    # 类似SQL的输入应作为普通ID，不得改变查询条件。
    connection, version_id = database
    assert get_champion(connection, version_id, identifier) is None
    assert get_ability(connection, version_id, identifier) is None


def test_version_isolation(database):
    # 未导入版本不能读到其他版本的英雄。
    connection, _ = database
    assert list_champions(connection, 2147483647) == []
    assert get_champion(connection, 2147483647, "TFT10_Annie") is None


def test_transaction_is_read_only(database):
    # 读取服务器实际设置验证只读模式，不尝试修改任何数据。
    connection, _ = database
    with connection.cursor() as cursor:
        cursor.execute("SHOW transaction_read_only")
        assert cursor.fetchone()[0] == "on"
