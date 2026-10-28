"""Separate immutable source attributes from mutable battle state."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChampionStats:
    # 只保存版本化源属性，不自动添加星级、装备或羁绊加成。
    version_id: int
    champion_id: str
    name: str
    max_hp: float
    attack_damage: float
    attack_speed: float
    armor: float
    magic_resist: float
    attack_range: float
    initial_mana: float
    max_mana: float

    def __post_init__(self) -> None:
        # 这是引擎输入边界，不将缺失值/无穷值当成可用战斗属性。
        values = (
            self.max_hp, self.attack_damage, self.attack_speed, self.armor,
            self.magic_resist, self.attack_range, self.initial_mana, self.max_mana,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Champion stats must be finite")
        if self.max_hp <= 0 or self.attack_speed <= 0 or self.attack_range <= 0:
            raise ValueError("HP, attack speed, and range must be positive")
        if self.attack_damage < 0 or not 0 <= self.initial_mana <= self.max_mana:
            raise ValueError("Invalid attack damage or mana range")

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ChampionStats":
        # 数据库hp表示源生命值；模型中命名max_hp，与战斗剩余生命值区分。
        return cls(
            version_id=int(record["version_id"]),
            champion_id=str(record["champion_id"]), name=str(record["name"]),
            max_hp=float(record["hp"]), attack_damage=float(record["attack_damage"]),
            attack_speed=float(record["attack_speed"]), armor=float(record["armor"]),
            magic_resist=float(record["magic_resist"]),
            attack_range=float(record["attack_range"]),
            initial_mana=float(record["initial_mana"]), max_mana=float(record["max_mana"]),
        )


@dataclass
class CombatState:
    # 每场战斗创建新实例；多个状态可以安全共享同一份不可变基础属性。
    stats: ChampionStats
    _current_hp: float = field(init=False, repr=False)
    current_mana: float = field(init=False)

    def __post_init__(self) -> None:
        # 初始化状态只读取源属性，不向数据库写入任何变化。
        self._current_hp = self.stats.max_hp
        self.current_mana = self.stats.initial_mana

    @property
    def current_hp(self) -> float:
        # 外部读取该属性，扣血统一通过take_damage处理边界。
        return self._current_hp

    @property
    def is_alive(self) -> bool:
        # 死亡状态由生命值推导，避免另存布尔值后与生命值不一致。
        return self._current_hp > 0

    def take_damage(self, amount: float) -> float:
        # 输入是已经结算好的伤害，不在这里计算护甲、暴击或技能倍率。
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Damage must be finite and nonnegative")
        # 实际扣血不超过剩余生命值；死亡后再次结算伤害返回0。
        damage_taken = min(amount, self._current_hp)
        self._current_hp = max(0.0, self._current_hp - damage_taken)
        return damage_taken
