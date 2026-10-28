"""Explicitly simplified single-target magic abilities."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


ABILITY_MODEL_VERSION = "instant_single_target_magic_v0.1_simplified"


@dataclass(frozen=True)
class SimplifiedMagicAbility:
    # 技能配置独立于源属性；身份绑定避免将Annie技能误装给其他英雄。
    version_id: int
    champion_id: str
    name: str
    raw_damage: float
    source_parameter: str
    source_index: int

    def __post_init__(self) -> None:
        # 不接受缺失伤害或非有限值，不将错误输入解释为治疗。
        if not math.isfinite(self.raw_damage) or self.raw_damage < 0:
            raise ValueError("Ability damage must be finite and nonnegative")


def build_annie_active(record: Mapping[str, Any]) -> SimplifiedMagicAbility:
    # 本轮只支持Annie主动部分，不根据其他英雄的描述猜测技能行为。
    if record["champion_id"] != "TFT10_Annie":
        raise ValueError("Only the simplified TFT10_Annie active is supported")
    parameters = [p for p in record["variables"] if p["name"] == "MagicDamage"]
    if len(parameters) != 1:
        raise ValueError("Expected exactly one MagicDamage source parameter")
    # 取明确的源数组索引1；不把数组长度转换为星级或生成高星属性。
    raw_damage = float(parameters[0]["value"][1])
    return SimplifiedMagicAbility(
        version_id=int(record["version_id"]), champion_id=record["champion_id"],
        name=record["ability_name"], raw_damage=raw_damage,
        source_parameter="MagicDamage", source_index=1,
    )
