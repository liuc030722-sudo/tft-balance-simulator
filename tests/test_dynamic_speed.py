"""Dynamic-speed formulas and event progress use synthetic fixtures."""

from dataclasses import replace

import pytest

from tft_simulator.combat.abilities import SimplifiedMagicAbility
from tft_simulator.combat.engine import run_duel
from tft_simulator.combat.passives import AttackHealPassive, build_olaf_passive, missing_health_attack_speed
from tft_simulator.combat.timing import TimingRules, reschedule_attack
from tft_simulator.combat.mana import ManaRules
from tft_simulator.models import ChampionStats


@pytest.fixture
def fighter():
    # 人工单位1秒攻击一次，生命100，伤害10，便于独立推导时间。
    return ChampionStats(1, "TEST_DYNAMIC", "Dynamic fixture", 100, 10, 1, 0, 0, 1, 0, 10)


def passive_for(stats, *, healing=0, bonus=0.0015):
    # 人工被动允许单独打开攻速或回血；不是额外真实英雄数据。
    return AttackHealPassive(stats.version_id, stats.champion_id, "Test passive", healing,
                             "TEST_ONLY", 1, bonus, 1)


def test_factory_reads_all_parameters():
    # 原始比例保持浮点精度，不把0.0015误当0.15倍。
    record = dict(version_id=1, champion_id="TFT10_Olaf", ability_name="Berserker Rage",
                  variables=[{"name": "HealValue", "value": [0, 20]},
                             {"name": "BonusAttackSpeed", "value": [0.0015, 0.0015]},
                             {"name": "PercentMissingHealth", "value": [1, 1]}])
    passive = build_olaf_passive(record)
    assert passive.heal_per_attack == 20
    assert passive.bonus_attack_speed_per_step == 0.0015
    assert passive.missing_health_percent_step == 1


@pytest.mark.parametrize("hp, expected", [(100, 0.65), (50, 0.69875), (0, 0.7475)])
def test_missing_hp_formula(fighter, hp, expected):
    # 满血无加成，半血增加7.5%；零血仅测试公式，死亡单位不排期。
    assert missing_health_attack_speed(0.65, hp, 100, passive_for(fighter)) == pytest.approx(expected)


def test_fractional_missing_hp_is_continuous(fighter):
    # 当前模型连续计算缺血百分比，不向下舍入到整数百分点。
    assert missing_health_attack_speed(1, 99.5, 100, passive_for(fighter)) == pytest.approx(1.00075)


@pytest.mark.parametrize("field, value", [
    ("bonus_attack_speed_per_step", -1), ("bonus_attack_speed_per_step", float("inf")),
    ("missing_health_percent_step", 0), ("missing_health_percent_step", float("nan")),
])
def test_invalid_passive_inputs(fighter, field, value):
    # 防止无效比例进入事件队列造成非法时间。
    with pytest.raises(ValueError):
        replace(passive_for(fighter), **{field: value})


@pytest.mark.parametrize("old, new, expected", [(1, 2, 0.75), (2, 1, 1.5), (1, 1, 1)])
def test_pending_progress_rescale(old, new, expected):
    # 当前0.5秒、原计划1秒；剩余时间按旧攻速/新攻速缩放。
    assert reschedule_attack(1, 0.5, old, new) == expected


@pytest.mark.parametrize("arguments", [(1, 1, 1, 2), (1, 0.5, 0, 2), (float("inf"), 0, 1, 2)])
def test_invalid_pending_schedule(arguments):
    # 不能把已到期攻击重新排入当前时间或接受非有限时间。
    with pytest.raises(ValueError):
        reschedule_attack(*arguments)


def test_attack_accelerates_before_own_first_hit(fighter):
    # 快速对手0.5秒造成50伤害，另一侧待执行第一击应按进度提前。
    enemy = replace(fighter, attack_speed=2, attack_damage=50)
    result = run_duel(enemy, fighter, max_duration=0.99, passive_b=passive_for(fighter))
    hits = [e for e in result.events if e.event_type == "attack" and e.actor_side == "B"]
    assert len(hits) == 1
    assert hits[0].time == pytest.approx(0.5 + 0.5 / 1.075)


def test_outside_window_attack_can_move_inside(fighter):
    # 原本1秒的攻击在0.98秒窗口外，但受到伤害后提前到约0.965秒。
    enemy = replace(fighter, attack_speed=2, attack_damage=50)
    result = run_duel(enemy, fighter, max_duration=0.98, passive_b=passive_for(fighter))
    assert result.attacks_b == 1 and result.duration == 0.98


def test_heal_recovery_slows_next_attack(fighter):
    # 人工1%/缺血百分点：半血1.5攻速，回血20后1.3，下一击应变慢。
    enemy = replace(fighter, attack_speed=2, attack_damage=50)
    result = run_duel(enemy, fighter, max_duration=0.9,
                      passive_b=passive_for(fighter, healing=20, bonus=0.01))
    changes = [e.attack_speed_b for e in result.events if e.event_type == "attack_speed_change"]
    assert changes == pytest.approx([1.5, 1.3])


def test_initial_spell_reschedules_first_attack(fighter):
    # 0秒满蓝技能造成半血，应将第一击从1秒提前到1/1.075秒。
    caster = replace(fighter, initial_mana=10, attack_damage=0)
    skill = SimplifiedMagicAbility(1, caster.champion_id, "Initial spell", 50, "TEST_ONLY", 1)
    result = run_duel(caster, fighter, max_duration=0.99, mana_rules=ManaRules(0),
                      ability_a=skill, passive_b=passive_for(fighter))
    hit = next(e for e in result.events if e.event_type == "attack")
    assert hit.actor_side == "B" and hit.time == pytest.approx(1 / 1.075)


def test_explicit_cap_applies_to_dynamic_speed(fighter):
    # 只应用显式实验上限，不声称1.02是游戏真实攻速上限。
    enemy = replace(fighter, attack_speed=1, attack_damage=50)
    result = run_duel(enemy, fighter, max_duration=1,
                      timing_rules=TimingRules(max_attack_speed=1.02), passive_b=passive_for(fighter))
    changed = [e for e in result.events if e.event_type == "attack_speed_change"]
    assert changed[-1].attack_speed_b == 1.02


def test_zero_bonus_preserves_old_timing(fighter):
    # 回血相同且攻速比例为零时，数值摘要和攻击时刻保持旧行为。
    heal_only = passive_for(fighter, healing=5, bonus=0)
    result = run_duel(fighter, fighter, max_duration=3, passive_b=heal_only)
    assert [e.time for e in result.events if e.event_type == "attack" and e.actor_side == "B"] == [1, 2, 3]
    assert result.metadata["dynamic_attack_speed"] is False


def test_both_dynamic_mirror_remains_simultaneous(fighter):
    # 对称动态单位保持同刻攻击，不能由A/B执行顺序引入先手优势。
    args = dict(passive_a=passive_for(fighter), passive_b=passive_for(fighter))
    result = run_duel(fighter, fighter, **args)
    assert result.reason == "double_ko"
    assert result.attacks_a == result.attacks_b == 10


def test_seeded_replay_and_monotonic_time(fighter):
    # 动态事件与暴击一起仍可重放，时间有序，输入不被修改。
    args = dict(enable_crit=True, seed=42, passive_b=passive_for(fighter, healing=3))
    first = run_duel(fighter, fighter, **args)
    assert first == run_duel(fighter, fighter, **args)
    assert [e.time for e in first.events] == sorted(e.time for e in first.events)
    assert fighter.attack_speed == 1


def test_event_budget_still_limits_dynamic_battle(fighter):
    # 动态排期不能绕开资源预算，错误不能伪装成平局。
    with pytest.raises(RuntimeError, match="limit"):
        run_duel(fighter, fighter, max_events=1, passive_b=passive_for(fighter))
