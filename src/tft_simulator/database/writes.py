"""Explicit maintenance CRUD; these functions never commit on their own."""

import math
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from tft_simulator.database.import_data import STAT_COLUMNS

# 允许维护的列固定列出；主键和版本归属不允许通过UPDATE改变。
CHAMPION_FIELDS = ("name", "cost", "traits", "role_raw", *STAT_COLUMNS)


def _checked_values(values: dict[str, Any]) -> dict[str, Any]:
    # 值由占位符绑定，字段名由白名单限制；浮点特殊值不得进入基础属性。
    result = dict(values)
    for field in STAT_COLUMNS:
        if field in result:
            number = float(result[field])
            if not math.isfinite(number):
                raise ValueError(f"Nonfinite champion stat: {field}")
            result[field] = number
    return result


def create_champion(
    connection: psycopg.Connection, version_id: int, record: dict[str, Any],
) -> dict[str, Any]:
    # 普通新增严格拒绝重复主键；重复CSV导入仍使用原有导入模块。
    if set(record) != {"champion_id", *CHAMPION_FIELDS}:
        raise ValueError("Champion record must contain exactly the documented fields")
    values = {"version_id": version_id, **_checked_values(record)}
    columns = ("version_id", "champion_id", *CHAMPION_FIELDS)
    statement = sql.SQL(
        "INSERT INTO public.champions ({}) VALUES ({}) RETURNING *"
    ).format(
        sql.SQL(", ").join(sql.Identifier(field) for field in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(statement, [values[field] for field in columns])
        return cursor.fetchone()


def update_champion(
    connection: psycopg.Connection, version_id: int,
    champion_id: str, changes: dict[str, Any],
) -> dict[str, Any] | None:
    # 只更新明确给出的列；空更新、修改主键或任意SQL字段一律拒绝。
    if not changes or not set(changes).issubset(CHAMPION_FIELDS):
        raise ValueError("Changes must contain nonempty permitted champion fields")
    values = _checked_values(changes)
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(field)) for field in values
    )
    statement = sql.SQL(
        "UPDATE public.champions SET {} "
        "WHERE version_id = %s AND champion_id = %s RETURNING *"
    ).format(assignments)
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(statement, [*values.values(), version_id, champion_id])
        return cursor.fetchone()


def delete_champion(
    connection: psycopg.Connection, version_id: int, champion_id: str,
) -> bool:
    # 仅删除精确匹配的单条记录；若有技能引用，外键会阻止删除，不级联清空。
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM public.champions WHERE version_id = %s AND champion_id = %s",
            (version_id, champion_id),
        )
        return cursor.rowcount == 1
