"""Source-backed, partial on-attack healing passive models."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any


PASSIVE_MODEL_VERSION = "olaf_heal_missing_hp_speed_v0.2_simplified"


@dataclass(frozen=True)
class AttackHealPassive:
    # 被动独立绑定版本和英雄，不用主动施法次数表示普攻触发次数。
    version_id: int
    champion_id: str
    name: str
    heal_per_attack: float
    source_parameter: str
    source_index: int
    bonus_attack_speed_per_step: float = 0.0
    missing_health_percent_step: float = 1.0

    def __post_init__(self) -> None:
        # 回血量允许零值对照，拒绝负数和非有限值。
        if not math.isfinite(self.heal_per_attack) or self.heal_per_attack < 0:
            raise ValueError("Healing must be finite and nonnegative")
        if not math.isfinite(self.bonus_attack_speed_per_step) or self.bonus_attack_speed_per_step < 0:
            raise ValueError("Attack speed bonus must be finite and nonnegative")
        if not math.isfinite(self.missing_health_percent_step) or self.missing_health_percent_step <= 0:
            raise ValueError("Missing health step must be finite and positive")


def build_olaf_healing(record: Mapping[str, Any]) -> AttackHealPassive:
    # 只支持Olaf的回血部分，不把缺血攻速或赛季之星效果标记为已实现。
    if record["champion_id"] != "TFT10_Olaf":
        raise ValueError("Only the partial TFT10_Olaf healing passive is supported")
    parameters = [p for p in record["variables"] if p["name"] == "HealValue"]
    if len(parameters) != 1:
        raise ValueError("Expected exactly one HealValue source parameter")
    return AttackHealPassive(
        version_id=int(record["version_id"]), champion_id=record["champion_id"],
        name=record["ability_name"], heal_per_attack=float(parameters[0]["value"][1]),
        source_parameter="HealValue", source_index=1,
    )


def build_olaf_passive(record: Mapping[str, Any]) -> AttackHealPassive:
    # 延用回血工厂的身份和来源，再显式加入两个缺血攻速源参数。
    healing = build_olaf_healing(record)
    values = {}
    for name in ("BonusAttackSpeed", "PercentMissingHealth"):
        entries = [p for p in record["variables"] if p["name"] == name]
        if len(entries) != 1:
            raise ValueError(f"Expected exactly one {name} source parameter")
        values[name] = float(entries[0]["value"][1])
    return replace(healing, bonus_attack_speed_per_step=values["BonusAttackSpeed"],
                   missing_health_percent_step=values["PercentMissingHealth"])


def missing_health_attack_speed(base_speed: float, current_hp: float,
                                max_hp: float, passive: AttackHealPassive) -> float:
    # 缺血百分比按连续值计算，不按1%台阶向下取整；这是显式简化约定。
    if not all(math.isfinite(v) for v in (base_speed, current_hp, max_hp)):
        raise ValueError("Speed and health must be finite")
    if base_speed <= 0 or max_hp <= 0 or not 0 <= current_hp <= max_hp:
        raise ValueError("Invalid speed or health range")
    missing_percent = (1.0 - current_hp / max_hp) * 100.0
    bonus = missing_percent / passive.missing_health_percent_step * passive.bonus_attack_speed_per_step
    speed = base_speed * (1.0 + bonus)
    if not math.isfinite(speed):
        raise ValueError("Dynamic attack speed exceeds finite float range")
    return speed
