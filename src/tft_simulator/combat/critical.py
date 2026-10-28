"""Independent per-attack critical rolls under an explicit model contract."""

import math
from dataclasses import dataclass
from random import Random

# 参数来自源数据，独立逐击掷骰与结算顺序属于模型定义，不代表全部TFT交互。
CRITICAL_MODEL_VERSION = "attack_crit_v0.1"


@dataclass(frozen=True)
class CriticalHit:
    # 同时保留基础攻击力、暴击后的原始伤害及随机数，方便解释单次结果。
    base_damage: float
    raw_damage: float
    is_critical: bool
    roll: float


def roll_critical_hit(
    base_damage: float, crit_chance: float, crit_multiplier: float, *, rng: Random,
) -> CriticalHit:
    # 0.25表示25%，1.4表示1.4倍；不把140当作倍数，也不接受未建模的溢出暴击率。
    if not all(math.isfinite(value) for value in (base_damage, crit_chance, crit_multiplier)):
        raise ValueError("Critical-hit inputs must be finite")
    if base_damage < 0 or not 0 <= crit_chance <= 1 or crit_multiplier < 1:
        raise ValueError("Invalid critical-hit inputs")
    # 每次调用消耗一个[0,1)随机数，0%和100%也保持相同的消耗规则。
    roll = rng.random()
    is_critical = roll < crit_chance
    raw_damage = base_damage * crit_multiplier if is_critical else base_damage
    if not math.isfinite(raw_damage):
        raise ValueError("Critical damage exceeds finite float range")
    return CriticalHit(base_damage, raw_damage, is_critical, roll)
