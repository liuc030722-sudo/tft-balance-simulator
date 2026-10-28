"""Synthetic tests for the experimental attack-mana extension."""

from dataclasses import replace

import pytest

from tft_simulator.combat.engine import run_duel
from tft_simulator.combat.mana import ManaRules, gain_attack_mana
from tft_simulator.models import ChampionStats, CombatState


@pytest.fixture
def fighter():
    # 人工属性只用于观察回蓝，不代表真实英雄数值。
    return ChampionStats(
        version_id=1, champion_id="TEST_MANA", name="Mana fixture",
        max_hp=100, attack_damage=1, attack_speed=1,
        armor=0, magic_resist=0, attack_range=1,
        initial_mana=0, max_mana=25,
    )


@pytest.mark.parametrize("amount", [-1, float("nan"), float("inf")])
def test_invalid_rule(amount):
    # 非法配置应在战斗前拒绝，避免污染动态法力值。
    with pytest.raises(ValueError):
        ManaRules(mana_per_attack=amount)


def test_partial_gain_and_cap(fighter):
    # 0→10→20→25→25，最后一次有效变化只有5。
    state = CombatState(fighter)
    rules = ManaRules(mana_per_attack=10)
    gains = [gain_attack_mana(state, rules=rules) for _ in range(4)]
    assert gains == [10, 10, 5, 0]
    assert state.current_mana == 25


def test_zero_max_mana(fighter):
    # 无法力槽单位不积累法力，也不引入除零问题。
    state = CombatState(replace(fighter, max_mana=0))
    assert gain_attack_mana(state, rules=ManaRules(10)) == 0


def test_dead_state_cannot_gain(fighter):
    # 已死亡状态不会因为批次里存在攻击而回蓝。
    state = CombatState(fighter)
    state.take_damage(100)
    assert gain_attack_mana(state, rules=ManaRules(10)) == 0
    assert state.current_mana == 0


def test_initial_mana_is_preserved(fighter):
    # 初始法力来自基础属性，不强制重置为零。
    state = CombatState(replace(fighter, initial_mana=22))
    assert gain_attack_mana(state, rules=ManaRules(10)) == 3


def test_engine_log_order_and_full_mana_no_cast(fighter):
    # 到达上限后继续普攻，但本步骤没有自动施法或清空法力。
    result = run_duel(fighter, fighter, max_duration=4, mana_rules=ManaRules(10))
    gains = [e for e in result.events if e.event_type == "mana_gain" and e.actor_side == "A"]
    assert [e.mana_change for e in gains] == [10, 10, 5]
    assert [e.mana_a for e in gains] == [10, 20, 25]
    assert result.events[-1].mana_a == result.events[-1].mana_b == 25
    assert result.attacks_a == result.attacks_b == 4
    assert result.metadata["skills"] is False
    assert result.metadata["mana_generation"] is True
    assert [e.event_type for e in result.events[1:5]] == ["attack", "attack", "mana_gain", "mana_gain"]


def test_simultaneous_lethal_hits_do_not_gain(fighter):
    # 同刻双杀先完成扣血，死亡双方都不能再回蓝。
    lethal = replace(fighter, attack_damage=100)
    result = run_duel(lethal, lethal, mana_rules=ManaRules(10))
    assert result.reason == "double_ko"
    assert not any(e.event_type == "mana_gain" for e in result.events)


def test_baseline_damage_and_seed_trace_unchanged(fighter):
    # 回蓝不改变普攻时间、随机数或胜负；只有法力状态和额外日志不同。
    arguments = dict(enable_crit=True, seed=42, max_duration=4)
    baseline = run_duel(fighter, fighter, **arguments)
    result = run_duel(fighter, fighter, mana_rules=ManaRules(10), **arguments)
    assert baseline.summary() == result.summary()
    assert [e.critical_roll for e in baseline.events if e.event_type == "attack"] == [
        e.critical_roll for e in result.events if e.event_type == "attack"
    ]
    assert baseline.events[-1].mana_a == 0


def test_zero_rule_and_repeatability(fighter):
    # 零回蓝对照和重复运行都不能悄悄保留上一场状态。
    first = run_duel(fighter, fighter, max_duration=4, mana_rules=ManaRules(10))
    assert first == run_duel(fighter, fighter, max_duration=4, mana_rules=ManaRules(10))
    zero = run_duel(fighter, fighter, max_duration=4, mana_rules=ManaRules(0))
    assert zero.events[-1].mana_a == 0
    assert not any(e.event_type == "mana_gain" for e in zero.events)


def test_invalid_engine_rule(fighter):
    # 拒绝字典等误传形式，提示调用者使用明确的配置类型。
    with pytest.raises(ValueError, match="ManaRules"):
        run_duel(fighter, fighter, mana_rules={"mana_per_attack": 10})
