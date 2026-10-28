"""Provisional resistance model, not certified Patch 14.1 engine behavior."""

import math

# 固定模型标识，之后模拟日志应记录它；不得把通过测试当作机制已获核验。
DAMAGE_MODEL_VERSION = "resistance_v0.1_unverified"


def resistance_multiplier(resistance: float) -> float:
    # 正抗性使用双曲线减伤；负抗性使用独立连续分支，避免-100处除零。
    # 两个分支均为当前项目的暂定规则，尚未以Patch 14.1一手资料完整核验。
    if not math.isfinite(resistance):
        raise ValueError("Resistance must be finite")
    if resistance >= 0:
        return 100.0 / (100.0 + resistance)
    return 2.0 - 100.0 / (100.0 - resistance)


def _validate_damage(raw_damage: float) -> None:
    # 负值不是伤害，不能被当作治疗；非有限值会污染后续状态。
    if not math.isfinite(raw_damage) or raw_damage < 0:
        raise ValueError("Damage must be finite and nonnegative")


def _apply_resistance(raw_damage: float, resistance: float) -> float:
    # 内部不取整；格式化显示的小数位不改变实际扣血精度。
    _validate_damage(raw_damage)
    result = raw_damage * resistance_multiplier(resistance)
    if not math.isfinite(result):
        raise ValueError("Calculated damage exceeds finite float range")
    return result


def physical_damage(raw_damage: float, armor: float) -> float:
    # 物理伤害只读取护甲，本步骤不处理穿透、技能减伤或护盾。
    return _apply_resistance(raw_damage, armor)


def magic_damage(raw_damage: float, magic_resist: float) -> float:
    # 魔法伤害使用魔抗，不能因为攻击者有法术技能而把普攻自动改成魔法。
    return _apply_resistance(raw_damage, magic_resist)


def true_damage(raw_damage: float) -> float:
    # 暂定模型中真实伤害绕过两种抗性；其他修正机制本轮不建模。
    _validate_damage(raw_damage)
    return raw_damage
