"""Opt-in CRUD tests using uncommitted synthetic records with forced rollback."""

import os
from uuid import uuid4

import psycopg
import pytest

from tft_simulator.database.connection import read_connection, write_connection
from tft_simulator.database.queries import get_champion, list_versions
from tft_simulator.database.writes import (
    create_champion, delete_champion, update_champion,
)


@pytest.fixture
def sandbox():
    # 测试只操作新建的TEST_ONLY记录，绝不把真实英雄作为UPDATE/DELETE目标。
    if os.getenv("TFT_TEST_DATABASE") != "1":
        pytest.skip("Set TFT_TEST_DATABASE=1 for transaction-isolated CRUD tests")
    identifier = f"TEST_ONLY_{uuid4().hex}"
    with write_connection() as connection:
        versions = [
            row for row in list_versions(connection)
            if row["set_number"] == 10 and row["patch"] == "14.1"
            and row["source_sha256"] ==
            "ae6d4bde7f591194b599caa120ca36ccc592bb5d9942ae703a47bd0cd0f7cb56"
        ]
        if len(versions) != 1:
            pytest.fail("Import the documented research snapshot first")
        version_id = versions[0]["version_id"]
        # 以下属性仅为人工测试夹具，不声称属于任何真实TFT英雄。
        record = {
            "champion_id": identifier, "name": "TEST_ONLY fixture", "cost": 1,
            "traits": ["TEST_ONLY"], "role_raw": None,
            "hp": 100.0, "attack_damage": 10.0, "attack_speed": 1.0,
            "armor": 0.0, "magic_resist": 0.0, "attack_range": 1.0,
            "initial_mana": 0.0, "max_mana": 10.0,
            "crit_chance": 0.0, "crit_multiplier": 1.0,
        }
        with connection.transaction(force_rollback=True):
            yield connection, version_id, record
        # 即使测试成功也回滚新增内容，并立即确认测试记录未残留。
        assert get_champion(connection, version_id, identifier) is None


def test_create_update_read_delete(sandbox):
    # 在同一测试记录上验证CRUD完整流程，真实英雄保持不变。
    connection, version_id, record = sandbox
    created = create_champion(connection, version_id, record)
    identifier = record["champion_id"]
    assert created["hp"] == 100.0
    changed = update_champion(connection, version_id, identifier, {"hp": 120.0})
    assert changed["hp"] == 120.0
    assert get_champion(connection, version_id, identifier)["hp"] == 120.0
    assert delete_champion(connection, version_id, identifier)
    assert get_champion(connection, version_id, identifier) is None
    assert not delete_champion(connection, version_id, identifier)


def test_duplicate_primary_key_is_rejected(sandbox):
    # SAVEPOINT隔离预期异常，使外层测试事务仍能继续查询。
    connection, version_id, record = sandbox
    create_champion(connection, version_id, record)
    with pytest.raises(psycopg.errors.UniqueViolation):
        with connection.transaction():
            create_champion(connection, version_id, record)
    assert get_champion(connection, version_id, record["champion_id"]) is not None


def test_skill_reference_blocks_delete(sandbox):
    # 仅给测试英雄添加测试技能，验证外键阻止直接删除父记录。
    connection, version_id, record = sandbox
    create_champion(connection, version_id, record)
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.abilities (version_id, champion_id, ability_name) "
            "VALUES (%s, %s, %s)",
            (version_id, record["champion_id"], "TEST_ONLY skill"),
        )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with connection.transaction():
            delete_champion(connection, version_id, record["champion_id"])
    assert get_champion(connection, version_id, record["champion_id"]) is not None


def test_check_constraint_preserves_existing_value(sandbox):
    # 非法生命值被数据库拒绝，失败更新不能改变该测试记录原来的值。
    connection, version_id, record = sandbox
    create_champion(connection, version_id, record)
    with pytest.raises(psycopg.errors.CheckViolation):
        with connection.transaction():
            update_champion(connection, version_id, record["champion_id"], {"hp": -1.0})
    assert get_champion(connection, version_id, record["champion_id"])["hp"] == 100.0


@pytest.mark.parametrize("changes", [{}, {"version_id": 2}, {"hp": float("nan")}])
def test_invalid_update_is_rejected(sandbox, changes):
    # 拒绝空更新、主键归属修改，以及数据库浮点类型可能接受的NaN。
    connection, version_id, record = sandbox
    with pytest.raises(ValueError):
        update_champion(connection, version_id, record["champion_id"], changes)


def test_unknown_id_does_not_update_other_heroes(sandbox):
    # 不存在的测试ID应返回None，不能遗漏WHERE条件而批量更新。
    connection, version_id, record = sandbox
    assert update_champion(connection, version_id, record["champion_id"], {"hp": 120.0}) is None


def test_read_connection_rejects_write():
    # 只读连接即便匹配不到记录，也不能执行UPDATE；目标绝非真实英雄。
    if os.getenv("TFT_TEST_DATABASE") != "1":
        pytest.skip("Set TFT_TEST_DATABASE=1 for local database tests")
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        with read_connection() as connection:
            update_champion(connection, 1, "TEST_ONLY_NOT_INSERTED", {"hp": 120.0})
