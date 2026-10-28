"""Read-only loading of source-backed combat profiles."""

import psycopg

from tft_simulator.combat.profiles import CombatantProfile, build_profile
from tft_simulator.database.queries import get_ability, get_champion, list_versions


def load_combatant(connection: psycopg.Connection, version_id: int,
                   champion_id: str, *, enable_skills: bool = False) -> CombatantProfile:
    # 数据访问只负责读取；模型构造和支持范围判断交给combat层。
    version = next((v for v in list_versions(connection) if v["version_id"] == version_id), None)
    champion = get_champion(connection, version_id, champion_id)
    if version is None or champion is None:
        raise ValueError("Source version or champion was not found")
    ability = get_ability(connection, version_id, champion_id) if enable_skills else None
    return build_profile(champion, version, ability, enable_skills=enable_skills)
