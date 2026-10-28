"""Read-only access to versioned champion source data."""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from tft_simulator.database.connection import read_connection

# 继续从queries模块提供read_connection，兼容已经发给用户的Notebook代码。


def list_versions(connection: psycopg.Connection) -> list[dict[str, Any]]:
    # 返回完整来源信息，不默认挑选所谓最新Patch，避免实验版本悄悄变化。
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SELECT * FROM public.game_versions ORDER BY version_id")
        return cursor.fetchall()


def list_champions(
    connection: psycopg.Connection, version_id: int, cost: int | None = None,
) -> list[dict[str, Any]]:
    # 版本必须显式指定；cost=None表示该版本的全部已导入英雄。
    if version_id <= 0:
        raise ValueError("version_id must be positive")
    if cost is not None and cost not in range(1, 6):
        raise ValueError("cost must be between 1 and 5")
    query = """
        SELECT c.version_id, c.champion_id, c.name, c.cost,
               c.role_raw, c.traits, c.hp, c.attack_damage, c.attack_speed,
               c.armor, c.magic_resist, a.ability_name
        FROM public.champions AS c
        LEFT JOIN public.abilities AS a
          ON a.version_id = c.version_id AND a.champion_id = c.champion_id
        WHERE c.version_id = %s
    """
    parameters: list[int] = [version_id]
    if cost is not None:
        # 只追加固定SQL片段；输入值始终作为独立参数传入。
        query += " AND c.cost = %s"
        parameters.append(cost)
    query += " ORDER BY c.cost, c.champion_id"
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters)
        return cursor.fetchall()


def get_champion(
    connection: psycopg.Connection, version_id: int, champion_id: str,
) -> dict[str, Any] | None:
    # 联合使用版本和英雄ID；找不到时返回None，不伪造默认属性。
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """SELECT * FROM public.champions
               WHERE version_id = %s AND champion_id = %s""",
            (version_id, champion_id),
        )
        return cursor.fetchone()


def get_ability(
    connection: psycopg.Connection, version_id: int, champion_id: str,
) -> dict[str, Any] | None:
    # psycopg自动将JSONB参数解码为Python列表/字典，不需要再次json.loads。
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """SELECT * FROM public.abilities
               WHERE version_id = %s AND champion_id = %s""",
            (version_id, champion_id),
        )
        return cursor.fetchone()


def get_counts(connection: psycopg.Connection, version_id: int) -> dict[str, int]:
    # 各项计数都限制在同一版本；不存在的版本返回三个0。
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """SELECT
                 (SELECT COUNT(*) FROM public.game_versions WHERE version_id=%s) AS versions,
                 (SELECT COUNT(*) FROM public.champions WHERE version_id=%s) AS champions,
                 (SELECT COUNT(*) FROM public.abilities WHERE version_id=%s) AS abilities""",
            (version_id, version_id, version_id),
        )
        return cursor.fetchone()
