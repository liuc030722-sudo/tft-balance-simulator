"""Experimental effect scaling, independent of immutable source records."""

import math
from dataclasses import replace

from tft_simulator.combat.abilities import SimplifiedMagicAbility
from tft_simulator.combat.passives import AttackHealPassive


ABILITY_POWER_MODEL_VERSION = "source_effect_percent_v0.1_experimental"


def validate_ability_power(percent: float) -> None:
    # 百分数是实验配置：100表示源效果不变，150表示1.5倍，不是加150%。
    if isinstance(percent, bool) or not isinstance(percent, (int, float)):
        raise ValueError("Ability power percent must be numeric")
    if not math.isfinite(percent) or percent < 0:
        raise ValueError("Ability power percent must be finite and nonnegative")


def scale_ability_effects(
    ability: SimplifiedMagicAbility | None,
    passive: AttackHealPassive | None, *, percent: float,
) -> tuple[SimplifiedMagicAbility | None, AttackHealPassive | None]:
    # 每次从源配置缩放，不在上次缩放结果上叠乘；不修改传入的数据类。
    validate_ability_power(percent)
    if percent == 100:
        return ability, passive
    if ability is None and passive is None:
        raise ValueError("No modeled ability effects to scale; enable supported skills first")
    factor = percent / 100.0
    # 当前仅让主动魔法伤害和普攻治疗线性缩放；缺血攻速、AD和法力保持原值。
    scaled_ability = replace(ability, raw_damage=ability.raw_damage * factor) if ability else None
    scaled_passive = replace(passive, heal_per_attack=passive.heal_per_attack * factor) if passive else None
    return scaled_ability, scaled_passive
