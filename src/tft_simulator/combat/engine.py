"""Event-driven duels with optional seeded critical strikes."""

import heapq
import math
import platform
from dataclasses import asdict, dataclass
from random import Random
from typing import Any, Literal

from tft_simulator.combat.damage import DAMAGE_MODEL_VERSION, physical_damage, magic_damage
from tft_simulator.combat.abilities import ABILITY_MODEL_VERSION, SimplifiedMagicAbility
from tft_simulator.combat.critical import CRITICAL_MODEL_VERSION, roll_critical_hit
from tft_simulator.combat.mana import MANA_MODEL_VERSION, ManaRules, gain_attack_mana
from tft_simulator.combat.passives import PASSIVE_MODEL_VERSION, AttackHealPassive, missing_health_attack_speed
from tft_simulator.combat.timing import (
    TIMING_MODEL_VERSION, TimingRules, effective_attack_speed,
    DYNAMIC_TIMING_MODEL_VERSION, reschedule_attack,
)
from tft_simulator.models import ChampionStats, CombatState

# 引擎版本记录的是本项目规则，不是Riot客户端实现版本。
ENGINE_VERSION = "basic_duel_v0.6"


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
    base_attack_damage: float = 0.0
    is_critical: bool = False
    critical_roll: float | None = None
    mana_change: float = 0.0
    healing: float = 0.0
    attack_speed_a: float = 0.0
    attack_speed_b: float = 0.0
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
    critical_hits_a: int
    critical_hits_b: int
    ability_casts_a: int
    ability_casts_b: int
    healing_a: float
    healing_b: float
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
            "critical_hits_a": self.critical_hits_a,
            "critical_hits_b": self.critical_hits_b,
            "ability_casts_a": self.ability_casts_a,
            "ability_casts_b": self.ability_casts_b,
            "healing_a": self.healing_a, "healing_b": self.healing_b,
        }

    def log_records(self) -> list[dict[str, Any]]:
        # 将日志数据类转换成可直接构建DataFrame或导出CSV的字典列表。
        return [asdict(event) for event in self.events]


@dataclass(frozen=True)
class _PendingAttack:
    # 批次中先保存攻击意图和随机结果，避免扣血顺序取消同刻已确定的攻击。
    actor: int
    target: int
    base_damage: float
    raw_damage: float
    mitigated: float
    is_critical: bool
    roll: float | None


def run_duel(
    stats_a: ChampionStats, stats_b: ChampionStats, *,
    max_duration: float = 60.0, timing_rules: TimingRules | None = None,
    max_events: int = 100_000,
    enable_crit: bool = False, seed: int | None = None,
    mana_rules: ManaRules | None = None,
    ability_a: SimplifiedMagicAbility | None = None,
    ability_b: SimplifiedMagicAbility | None = None,
    passive_a: AttackHealPassive | None = None,
    passive_b: AttackHealPassive | None = None,
) -> BattleResult:
    # 同一实验限制在同一源版本；每次调用新建状态，不沿用Notebook中的受伤状态。
    if stats_a.version_id != stats_b.version_id:
        raise ValueError("Both champions must use the same source version")
    if not math.isfinite(max_duration) or max_duration < 0:
        raise ValueError("max_duration must be finite and nonnegative")
    if not isinstance(max_events, int) or max_events <= 0:
        raise ValueError("max_events must be a positive integer")
    if not isinstance(enable_crit, bool):
        raise ValueError("enable_crit must be boolean")
    if mana_rules is not None and not isinstance(mana_rules, ManaRules):
        raise ValueError("mana_rules must be ManaRules or None")
    if enable_crit and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError("An explicit integer seed is required when critical strikes are enabled")
    if not enable_crit and seed is not None:
        raise ValueError("A seed has no effect when critical strikes are disabled; omit it")
    # 每场创建局部生成器，不使用全局random.seed，不受Notebook其他随机代码影响。
    rng = Random(seed) if enable_crit else None
    rules = timing_rules if timing_rules is not None else TimingRules()
    stats = (stats_a, stats_b)
    abilities = (ability_a, ability_b)
    passives = (passive_a, passive_b)
    for actor, passive in enumerate(passives):
        # 被动和主动分别校验，零法力槽单位也可以拥有被动。
        if passive is not None:
            if not isinstance(passive, AttackHealPassive):
                raise ValueError("Passives must be AttackHealPassive or None")
            if (passive.version_id, passive.champion_id) != (stats[actor].version_id, stats[actor].champion_id):
                raise ValueError("Passive version/champion does not match combatant")
    for actor, ability in enumerate(abilities):
        # 配置只绑定当前版本英雄；零法力槽和未配置回蓝不进入此施法模型。
        if ability is not None:
            if not isinstance(ability, SimplifiedMagicAbility):
                raise ValueError("Abilities must be SimplifiedMagicAbility or None")
            if (ability.version_id, ability.champion_id) != (stats[actor].version_id, stats[actor].champion_id):
                raise ValueError("Ability version/champion does not match combatant")
            if stats[actor].max_mana <= 0 or mana_rules is None:
                raise ValueError("Casting requires positive max_mana and explicit mana_rules")
    states = (CombatState(stats_a), CombatState(stats_b))
    sides = ("A", "B")
    speeds = [effective_attack_speed(s.attack_speed, rules=rules) for s in stats]
    dynamic = [p is not None and p.bonus_attack_speed_per_step > 0 for p in passives]
    attacks = [0, 0]
    damage_dealt = [0.0, 0.0]
    critical_hits = [0, 0]
    ability_casts = [0, 0]
    healing_done = [0.0, 0.0]
    events: list[BattleEvent] = []
    current_time = 0.0

    def log_event(
        kind: str, actor: int | None = None, target: int | None = None, *,
        raw: float = 0.0, mitigated: float = 0.0,
        actual: float = 0.0, detail: str = "",
        base_damage: float = 0.0, is_critical: bool = False, roll: float | None = None,
        mana_change: float = 0.0,
        healing: float = 0.0,
    ) -> None:
        # 日志保存当前快照；法力事件的mana_change表示该行动者实际回蓝量。
        events.append(BattleEvent(
            time=current_time, event_type=kind,
            actor_side=sides[actor] if actor is not None else None,
            actor=stats[actor].name if actor is not None else None,
            target_side=sides[target] if target is not None else None,
            target=stats[target].name if target is not None else None,
            raw_damage=raw, damage_after_resistance=mitigated, damage=actual,
            hp_a=states[0].current_hp, hp_b=states[1].current_hp,
            mana_a=states[0].current_mana, mana_b=states[1].current_mana,
            base_attack_damage=base_damage, is_critical=is_critical, critical_roll=roll,
            mana_change=mana_change,
            healing=healing,
            attack_speed_a=speeds[0], attack_speed_b=speeds[1],
            detail=detail,
        ))

    log_event("battle_start")
    # 小根堆保存每侧下一次攻击：时间、位置索引、攻击序号。
    queue: list[tuple[float, int, int]] = []
    # 初始满蓝时在0秒执行一次技能阶段；-1只是内部唤醒标记，不是攻击者。
    if any(ability is not None and stats[i].initial_mana == stats[i].max_mana
           for i, ability in enumerate(abilities)):
        heapq.heappush(queue, (0.0, -1, 0))
    for actor in (0, 1):
        first_time = 1.0 / speeds[actor]
        # 动态单位保留窗口外的下一击，之后加速可能将它提前到窗口内。
        if dynamic[actor] or first_time <= max_duration:
            heapq.heappush(queue, (first_time, actor, 1))

    winner: Literal["A", "B", "draw"] = "draw"
    reason = "timeout"
    while queue and queue[0][0] <= max_duration:
        current_time = queue[0][0]
        batch: list[tuple[float, int, int]] = []
        # 严格相同的浮点时间作为同时事件，不人为把相邻时间合并。
        while queue and queue[0][0] == current_time:
            batch.append(heapq.heappop(queue))
        attack_batch = [entry for entry in batch if entry[1] >= 0]
        if sum(attacks) + sum(ability_casts) + len(attack_batch) > max_events:
            # 计算资源不足不等于游戏平局；抛出错误，不产生虚假战斗结果。
            raise RuntimeError("Attack-event limit exceeded; no result produced")

        pending: list[_PendingAttack] = []
        for _, actor, _ in attack_batch:
            target = 1 - actor
            if states[actor].is_alive and states[target].is_alive:
                # 先根据批次开始时的存活状态生成全部攻击，再统一扣血。
                base_damage = stats[actor].attack_damage
                if rng is not None:
                    # 暴击先改变护甲计算前的伤害；后续抗性函数保持不变。
                    hit = roll_critical_hit(
                        base_damage, stats[actor].crit_chance,
                        stats[actor].crit_multiplier, rng=rng,
                    )
                    raw, is_critical, roll = hit.raw_damage, hit.is_critical, hit.roll
                else:
                    raw, is_critical, roll = base_damage, False, None
                mitigated = physical_damage(raw, stats[target].armor)
                pending.append(_PendingAttack(
                    actor, target, base_damage, raw, mitigated, is_critical, roll,
                ))

        resolved: list[tuple[_PendingAttack, float]] = []
        for hit in pending:
            actual = states[hit.target].take_damage(hit.mitigated)
            attacks[hit.actor] += 1
            damage_dealt[hit.actor] += actual
            critical_hits[hit.actor] += int(hit.is_critical)
            resolved.append((hit, actual))
        for hit, actual in resolved:
            log_event(
                "attack", hit.actor, hit.target, raw=hit.raw_damage,
                mitigated=hit.mitigated, actual=actual, base_damage=hit.base_damage,
                is_critical=hit.is_critical, roll=hit.roll,
            )

        # 治疗阶段在整批普攻伤害之后；只处理实际完成攻击的存活单位。
        healed = []
        for hit, _ in resolved:
            passive = passives[hit.actor]
            if passive is not None:
                actual_heal = states[hit.actor].heal(passive.heal_per_attack)
                healing_done[hit.actor] += actual_heal
                if actual_heal > 0:
                    healed.append((hit.actor, passive, actual_heal))
        # 同刻治疗全部应用后记录快照，日志顺序不改变治疗结果。
        for actor, passive, actual_heal in healed:
            log_event("heal", actor, actor, healing=actual_heal,
                      detail=f"{passive.name}; on_attack_healing")

        # 攻击日志先记录回蓝前的法力；新增独立事件说明回蓝后的状态。
        if mana_rules is not None:
            for hit, _ in resolved:
                gained = gain_attack_mana(states[hit.actor], rules=mana_rules)
                if gained > 0:
                    log_event(
                        "mana_gain", hit.actor, mana_change=gained,
                        detail="experimental_attack_mana",
                    )

        # 双方都存活才进入技能阶段；普攻击杀后不再对尸体施法。
        if all(state.is_alive for state in states):
            ready = [i for i, ability in enumerate(abilities)
                     if ability is not None and states[i].current_mana >= stats[i].max_mana]
            if sum(attacks) + sum(ability_casts) + len(ready) > max_events:
                raise RuntimeError("Combat-event limit exceeded; no result produced")
            # 同刻满蓝技能先确定伤害和消耗，再一起结算，允许技能双杀。
            casts = []
            for actor in ready:
                ability = abilities[actor]
                target = 1 - actor
                mitigated = magic_damage(ability.raw_damage, stats[target].magic_resist)
                spent = states[actor].current_mana
                states[actor].current_mana = 0.0
                ability_casts[actor] += 1
                casts.append((actor, target, ability, mitigated, spent))
            cast_results = []
            for actor, target, ability, mitigated, spent in casts:
                actual = states[target].take_damage(mitigated)
                damage_dealt[actor] += actual
                cast_results.append((actor, target, ability, mitigated, spent, actual))
            for actor, target, ability, mitigated, spent, actual in cast_results:
                log_event(
                    "ability_cast", actor, target, raw=ability.raw_damage,
                    mitigated=mitigated, actual=actual, mana_change=-spent,
                    detail=f"{ability.name}; simplified_instant_magic; active_only",
                )

        dead = [actor for actor in (0, 1) if not states[actor].is_alive]
        for actor in dead:
            log_event("death", actor, detail="hp_zero")
        if dead:
            # 同一批次允许双杀，不用A/B的处理顺序决定胜负。
            reason = "double_ko" if len(dead) == 2 else "death"
            winner = "draw" if len(dead) == 2 else sides[1 - dead[0]]
            break

        # 本时刻伤害、回血、技能全部完成后重算攻速；保留另一侧待执行攻击进度。
        for actor in (0, 1):
            if not dynamic[actor]:
                continue
            old_speed = speeds[actor]
            new_speed = effective_attack_speed(missing_health_attack_speed(
                stats[actor].attack_speed, states[actor].current_hp,
                stats[actor].max_hp, passives[actor],
            ), rules=rules)
            if new_speed != old_speed:
                queue = [
                    (reschedule_attack(time, current_time, old_speed, new_speed), side, number)
                    if side == actor else (time, side, number)
                    for time, side, number in queue
                ]
                heapq.heapify(queue)
                speeds[actor] = new_speed
                log_event("attack_speed_change", actor,
                          detail=f"missing_health_continuous; old={old_speed}; new={new_speed}")

        for _, actor, attack_number in attack_batch:
            next_number = attack_number + 1
            # 动态单位按当前攻速等待下一完整间隔；静态单位保留旧绝对排期。
            next_time = current_time + 1.0 / speeds[actor] if dynamic[actor] else next_number / speeds[actor]
            if next_time <= current_time:
                raise RuntimeError("Attack time no longer advances at float precision")
            if dynamic[actor] or next_time <= max_duration:
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
        critical_hits_a=critical_hits[0], critical_hits_b=critical_hits[1],
        ability_casts_a=ability_casts[0], ability_casts_b=ability_casts[1],
        healing_a=healing_done[0], healing_b=healing_done[1],
        metadata={
            "engine_version": ENGINE_VERSION,
            "damage_model": DAMAGE_MODEL_VERSION, "timing_model": TIMING_MODEL_VERSION,
            "source_version_id": stats_a.version_id,
            "champion_a": stats_a.champion_id, "champion_b": stats_b.champion_id,
            "stats_a": asdict(stats_a), "stats_b": asdict(stats_b),
            "max_duration": max_duration, "max_events": max_events,
            "timing_rules": asdict(rules),
            "simultaneous_rule": "exact_timestamp_batch_then_death",
            "always_in_range": True,
            "randomness": "attack_critical_rolls" if enable_crit else "none",
            "critical_model": CRITICAL_MODEL_VERSION if enable_crit else None,
            "random_seed": seed, "python_version": platform.python_version(),
            "rng_order": "chronological; A before B within exact timestamp ties" if enable_crit else None,
            "skills": any(ability is not None for ability in abilities),
            "ability_model": ABILITY_MODEL_VERSION if any(abilities) else None,
            "abilities": [asdict(ability) if ability is not None else None for ability in abilities],
            "skill_status": ["simplified_active_only" if ability else "not_modeled" for ability in abilities],
            "cast_resolution": "instant; after_attack_damage_and_mana; simultaneous_cast_batch; initial_full_mana_at_zero",
            "critical_strikes": enable_crit, "items": False,
            "passives": any(passives),
            "passive_model": PASSIVE_MODEL_VERSION if any(passives) else None,
            "passive_configs": [asdict(passive) if passive else None for passive in passives],
            "passive_status": ["simplified_heal_and_missing_hp_speed" if dynamic[i] else
                               "partial_heal_only" if passive else "not_modeled"
                               for i, passive in enumerate(passives)],
            "passive_resolution": "after_attack_damage; before_mana_and_casts; surviving_attackers_only",
            "dynamic_attack_speed": any(dynamic),
            "dynamic_timing_model": DYNAMIC_TIMING_MODEL_VERSION if any(dynamic) else None,
            "dynamic_timing_resolution": "after_damage_heal_and_casts; continuous_missing_hp; preserve_pending_progress" if any(dynamic) else None,
            "traits": False, "movement": False,
            "mana_generation": mana_rules is not None,
            "mana_model": MANA_MODEL_VERSION if mana_rules is not None else None,
            "mana_rules": asdict(mana_rules) if mana_rules is not None else None,
            "mana_resolution": "after_attack_batch_damage; surviving_attackers_only",
            "special_attack_rules": False,
        },
    )
