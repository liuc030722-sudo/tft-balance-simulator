"""Import versioned champion and ability CSV files without overwriting rows."""

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from tft_simulator.config import load_settings

# 与现有表的属性列顺序一致；不计算星级、装备或技能效果。
STAT_COLUMNS = (
    "hp", "attack_damage", "attack_speed", "armor", "magic_resist",
    "attack_range", "initial_mana", "max_mana", "crit_chance", "crit_multiplier",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    # DictReader按列名读取；utf-8-sig兼容此前为Windows导出的CSV。
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_dataset(
    champion_path: Path, ability_path: Path, manifest_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    # 复用已有来源记录，不生成额外哈希或导出清单。
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = {
        "set_number": int(source["set_number"]),
        "patch": source["patch_directory"],
        "source_url": source["source_url"],
        "source_sha256": source["sha256"],
        "retrieved_at_utc": datetime.fromisoformat(source["retrieved_at_utc"]),
    }
    if version["retrieved_at_utc"].utcoffset() is None:
        raise ValueError("Source retrieval time must include a timezone")

    champions: list[dict[str, Any]] = []
    abilities: list[dict[str, Any]] = []
    for rows, output, is_champion in (
        (read_csv(champion_path), champions, True),
        (read_csv(ability_path), abilities, False),
    ):
        seen: set[str] = set()
        for row in rows:
            # 入库前阻止重复ID及混入其他版本，避免静默丢行或关联错误。
            identifier = row["champion_id"]
            if not identifier or identifier in seen:
                raise ValueError("Empty or duplicate champion ID in CSV")
            seen.add(identifier)
            if (
                int(row["set_number"]) != version["set_number"]
                or row["patch"] != version["patch"]
                or row["source_url"] != version["source_url"]
                or row["source_sha256"] != version["source_sha256"]
            ):
                raise ValueError("CSV provenance does not match source manifest")

            record: dict[str, Any] = {"champion_id": identifier}
            if is_champion:
                record.update(
                    name=row["name"], cost=int(row["cost"]),
                    traits=json.loads(row["traits_json"]),
                    role_raw=row["role_raw"] or None,
                )
                if not isinstance(record["traits"], list) or not all(
                    isinstance(value, str) for value in record["traits"]
                ):
                    raise ValueError("traits_json must contain a string list")
                for column in STAT_COLUMNS:
                    # 空值或非有限值不转换成零；发现问题直接停止导入。
                    number = float(row[column])
                    if not math.isfinite(number):
                        raise ValueError(f"Nonfinite champion stat: {column}")
                    record[column] = number
            else:
                record.update(
                    ability_name=row["ability_name"] or None,
                    description_raw=row["description_raw"] or None,
                    variables=json.loads(row["variables_json"]),
                )
                if record["variables"] is not None and not isinstance(record["variables"], list):
                    raise ValueError("Skill variables must be an array or null")
            output.append(record)

    if not champions or {r["champion_id"] for r in champions} != {
        r["champion_id"] for r in abilities
    }:
        raise ValueError("Champion and ability CSV files must have matching nonempty IDs")
    return version, champions, abilities


def import_dataset(
    connection: psycopg.Connection,
    version: dict[str, Any],
    champions: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
) -> dict[str, int]:
    # 同一个事务保证版本、英雄、技能一起成功；失败时回滚本次新增内容。
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        if cursor.fetchone()[0] != "tft_balance_simulator":
            raise ValueError("Refusing to import into a different database")
        cursor.execute(
            """INSERT INTO public.game_versions
               (set_number, patch, source_url, source_sha256, retrieved_at_utc)
               VALUES (%(set_number)s, %(patch)s, %(source_url)s,
                       %(source_sha256)s, %(retrieved_at_utc)s)
               ON CONFLICT (set_number, patch, source_sha256) DO NOTHING
               RETURNING version_id""", version,
        )
        inserted = cursor.fetchone()
        new_versions = int(inserted is not None)
        if inserted is None:
            # 重复导入时复用现有版本，不更新其来源信息或已保存记录。
            cursor.execute(
                """SELECT version_id FROM public.game_versions
                   WHERE set_number=%(set_number)s AND patch=%(patch)s
                     AND source_sha256=%(source_sha256)s""", version,
            )
            inserted = cursor.fetchone()
        version_id = inserted[0]

        cursor.executemany(
            """INSERT INTO public.champions
               (version_id, champion_id, name, cost, traits, role_raw,
                hp, attack_damage, attack_speed, armor, magic_resist,
                attack_range, initial_mana, max_mana, crit_chance, crit_multiplier)
               VALUES (%(version_id)s, %(champion_id)s, %(name)s, %(cost)s,
                       %(traits)s, %(role_raw)s, %(hp)s, %(attack_damage)s,
                       %(attack_speed)s, %(armor)s, %(magic_resist)s,
                       %(attack_range)s, %(initial_mana)s, %(max_mana)s,
                       %(crit_chance)s, %(crit_multiplier)s)
               ON CONFLICT (version_id, champion_id) DO NOTHING""",
            [dict(row, version_id=version_id) for row in champions],
        )
        new_champions = cursor.rowcount
        cursor.executemany(
            """INSERT INTO public.abilities
               (version_id, champion_id, ability_name, description_raw, variables)
               VALUES (%(version_id)s, %(champion_id)s, %(ability_name)s,
                       %(description_raw)s, %(variables)s)
               ON CONFLICT (version_id, champion_id) DO NOTHING""",
            [dict(
                row, version_id=version_id,
                variables=Jsonb(row["variables"]) if row["variables"] is not None else None,
            ) for row in abilities],
        )
        new_abilities = cursor.rowcount
    return {
        "version_id": version_id, "new_versions": new_versions,
        "new_champions": new_champions, "new_abilities": new_abilities,
    }


def main() -> None:
    # 显式指定文件，不猜测哪个导出批次应当入库；凭据仅从既有配置加载。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--champions", type=Path, required=True)
    parser.add_argument("--abilities", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    dataset = load_dataset(args.champions, args.abilities, args.manifest)
    with psycopg.connect(**load_settings().connection_kwargs(), autocommit=True) as connection:
        result = import_dataset(connection, *dataset)
    print(json.dumps(result))


if __name__ == "__main__":
    # python -m形式使用包路径，避免Notebook状态或当前导入路径的影响。
    main()
