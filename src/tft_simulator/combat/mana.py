"""Explicit experimental mana rules; not a verified TFT patch implementation."""

import math
from dataclasses import dataclass

from tft_simulator.models import CombatState


MANA_MODEL_VERSION = "attack_mana_v0.1_experimental"


@dataclass(frozen=True)
class ManaRules:
    # 必须显式传入实验回蓝量，不将猜测的数值作为官方默认值。
    mana_per_attack: float

    def __post_init__(self) -> None:
        # 允许零回蓝作为对照，但不允许负数和非有限值。
        if not math.isfinite(self.mana_per_attack) or self.mana_per_attack < 0:
            raise ValueError("mana_per_attack must be finite and nonnegative")


def gain_attack_mana(state: CombatState, *, rules: ManaRules) -> float:
    # 当前简化规则：同刻伤害全部结算后，仍存活的攻击者才获得法力。
    if not state.is_alive:
        return 0.0
    # 先限制可补充的空间，避免加法溢出；零最大法力也会自然返回零。
    missing_mana = state.stats.max_mana - state.current_mana
    gained = min(rules.mana_per_attack, missing_mana)
    before = state.current_mana
    state.current_mana = min(state.stats.max_mana, before + gained)
    # 返回实际变化，而不是请求量，日志才能正确显示上限处的部分回蓝。
    return state.current_mana - before
