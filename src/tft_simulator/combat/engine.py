"""Deterministic event-driven duel under explicitly simplified combat rules."""

import heapq
import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from tft_simulator.combat.damage import DAMAGE_MODEL_VERSION, physical_damage
from tft_simulator.combat.timing import (
    TIMING_MODEL_VERSION, TimingRules, effective_attack_speed,
)
from tft_simulator.models import ChampionStats, CombatState

# 引擎版本记录的是本项目规则，不是Riot客户端实现版本。
ENGINE_VERSION = "basic_duel_v0.1"


@dataclass(frozen=True)
class BattleEvent:
    # 同一时间批次的攻击日志都记录该批次结算完毕后的生命值快照。
    time: float
    event_type: str
    actor_side: str | None
    actor: str | None
    target_side: str | None
    target: str | None
    raw_damage: float
    damage_after_resistance: float
    damage: float
    hp_a: float
    hp_b: float
    mana_a: float
    mana_b: float
    detail: str = ""


@dataclass(frozen=True)
class BattleResult:
    # winner使用A/B区分位置，允许同名同ID英雄进行镜像对战。
    winner: Literal["A", "B", "draw"]
    winner_name: str | None
    reason: str
    duration: float
    hp_a: float
    hp_b: float
    attacks_a: int
    attacks_b: int
    damage_a: float
    damage_b: float
    events: tuple[BattleEvent, ...]
    metadata: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        # 返回简洁摘要，避免Notebook直接展开整份事件日志。
        return {
            "winner": self.winner, "winner_name": self.winner_name,
            "reason": self.reason, "duration": self.duration,
            "hp_a": self.hp_a, "hp_b": self.hp_b,
            "attacks_a": self.attacks_a, "attacks_b": self.attacks_b,
            "damage_a": self.damage_a, "damage_b": self.damage_b,
        }

    def log_records(self) -> list[dict[str, Any]]:
        # 将日志数据类转换成可直接构建DataFrame或导出CSV的字典列表。
        return [asdict(event) for event in self.events]


def run_duel(
    stats_a: ChampionStats, stats_b: ChampionStats, *,
    max_duration: float = 60.0, timing_rules: TimingRules | None = None,
    max_events: int = 100_000,
) -> BattleResult:
    # 同一实验限制在同一源版本；每次调用新建状态，不沿用Notebook中的受伤状态。
    if stats_a.version_id != stats_b.version_id:
        raise ValueError("Both champions must use the same source version")
    if not math.isfinite(max_duration) or max_duration < 0:
        raise ValueError("max_duration must be finite and nonnegative")
    if not isinstance(max_events, int) or max_events <= 0:
        raise ValueError("max_events must be a positive integer")
    rules = timing_rules if timing_rules is not None else TimingRules()
    stats = (stats_a, stats_b)
    states = (CombatState(stats_a), CombatState(stats_b))
    sides = ("A", "B")
    speeds = tuple(effective_attack_speed(s.attack_speed, rules=rules) for s in stats)
    attacks = [0, 0]
    damage_dealt = [0.0, 0.0]
    events: list[BattleEvent] = []
    current_time = 0.0

    def log_event(
        kind: str, actor: int | None = None, target: int | None = None, *,
        raw: float = 0.0, mitigated: float = 0.0,
        actual: float = 0.0, detail: str = "",
    ) -> None:
        # 生命值和法力值只读快照；当前模型没有法力获取或施法。
        events.append(BattleEvent(
            time=current_time, event_type=kind,
            actor_side=sides[actor] if actor is not None else None,
            actor=stats[actor].name if actor is not None else None,
            target_side=sides[target] if target is not None else None,
            target=stats[target].name if target is not None else None,
            raw_damage=raw, damage_after_resistance=mitigated, damage=actual,
            hp_a=states[0].current_hp, hp_b=states[1].current_hp,
            mana_a=states[0].current_mana, mana_b=states[1].current_mana,
            detail=detail,
        ))

    log_event("battle_start")
    # 小根堆保存每侧下一次攻击：时间、位置索引、攻击序号。
    queue: list[tuple[float, int, int]] = []
    for actor in (0, 1):
        first_time = 1.0 / speeds[actor]
        if first_time <= max_duration:
            heapq.heappush(queue, (first_time, actor, 1))

    winner: Literal["A", "B", "draw"] = "draw"
    reason = "timeout"
    while queue:
        current_time = queue[0][0]
        batch: list[tuple[float, int, int]] = []
        # 严格相同的浮点时间作为同时事件，不人为把相邻时间合并。
        while queue and queue[0][0] == current_time:
            batch.append(heapq.heappop(queue))
        if sum(attacks) + len(batch) > max_events:
            # 计算资源不足不等于游戏平局；抛出错误，不产生虚假战斗结果。
            raise RuntimeError("Attack-event limit exceeded; no result produced")

        pending: list[tuple[int, int, float, float]] = []
        for _, actor, _ in batch:
            target = 1 - actor
            if states[actor].is_alive and states[target].is_alive:
                # 先根据批次开始时的存活状态生成全部攻击，再统一扣血。
                raw = stats[actor].attack_damage
                mitigated = physical_damage(raw, stats[target].armor)
                pending.append((actor, target, raw, mitigated))

        resolved: list[tuple[int, int, float, float, float]] = []
        for actor, target, raw, mitigated in pending:
            actual = states[target].take_damage(mitigated)
            attacks[actor] += 1
            damage_dealt[actor] += actual
            resolved.append((actor, target, raw, mitigated, actual))
        for actor, target, raw, mitigated, actual in resolved:
            log_event("attack", actor, target, raw=raw, mitigated=mitigated, actual=actual)

        dead = [actor for actor in (0, 1) if not states[actor].is_alive]
        for actor in dead:
            log_event("death", actor, detail="hp_zero")
        if dead:
            # 同一批次允许双杀，不用A/B的处理顺序决定胜负。
            reason = "double_ko" if len(dead) == 2 else "death"
            winner = "draw" if len(dead) == 2 else sides[1 - dead[0]]
            break

        for _, actor, attack_number in batch:
            next_number = attack_number + 1
            next_time = next_number / speeds[actor]
            if next_time <= current_time:
                raise RuntimeError("Attack time no longer advances at float precision")
            if next_time <= max_duration:
                heapq.heappush(queue, (next_time, actor, next_number))
    else:
        # 超时平局的时长为窗口上限，不是最后一个攻击事件的时间。
        current_time = max_duration

    log_event("battle_end", detail=f"winner={winner}; reason={reason}")
    winner_name = stats[0 if winner == "A" else 1].name if winner != "draw" else None
    return BattleResult(
        winner=winner, winner_name=winner_name, reason=reason,
        duration=current_time, hp_a=states[0].current_hp, hp_b=states[1].current_hp,
        attacks_a=attacks[0], attacks_b=attacks[1],
        damage_a=damage_dealt[0], damage_b=damage_dealt[1], events=tuple(events),
        metadata={
            "engine_version": ENGINE_VERSION,
            "damage_model": DAMAGE_MODEL_VERSION, "timing_model": TIMING_MODEL_VERSION,
            "source_version_id": stats_a.version_id,
            "champion_a": stats_a.champion_id, "champion_b": stats_b.champion_id,
            "stats_a": asdict(stats_a), "stats_b": asdict(stats_b),
            "max_duration": max_duration, "max_events": max_events,
            "timing_rules": asdict(rules),
            "simultaneous_rule": "exact_timestamp_batch_then_death",
            "always_in_range": True, "randomness": "none",
            "skills": False, "critical_strikes": False, "items": False,
            "passives": False, "traits": False, "movement": False,
            "mana_generation": False, "special_attack_rules": False,
        },
    )
