"""Synthetic fixtures test declared skill semantics, not TFT fidelity."""

from dataclasses import replace

import pytest

from tft_simulator.combat.abilities import SimplifiedMagicAbility, build_annie_active
from tft_simulator.combat.engine import run_duel
from tft_simulator.combat.mana import ManaRules
from tft_simulator.models import ChampionStats


@pytest.fixture
def fighter():
    # 人工属性让每两次普攻施法一次，便于精确验证时序。
    return ChampionStats(
        version_id=1, champion_id="TEST_SKILL", name="Skill fixture",
        max_hp=1000, attack_damage=1, attack_speed=1,
        armor=0, magic_resist=0, attack_range=1, initial_mana=0, max_mana=20,
    )


def ability_for(stats, damage=100):
    # 这是人工技能夹具；生产Annie配置通过源记录工厂读取。
    return SimplifiedMagicAbility(stats.version_id, stats.champion_id, "Test magic", damage, "TEST_ONLY", 1)


def test_source_factory_retains_identity_and_parameter():
    # 只验证源字段提取，不把测试数组误称为新采集数据。
    ability = build_annie_active(dict(
        version_id=7, champion_id="TFT10_Annie", ability_name="Disintegrate",
        variables=[{"name": "MagicDamage", "value": [0, 220, 330, 495]}],
    ))
    assert ability.raw_damage == 220
    assert ability.source_parameter == "MagicDamage" and ability.source_index == 1
    assert ability.version_id == 7


def test_unsupported_source_rejected():
    # 不根据相似伤害字段把其他英雄误标成已经支持。
    with pytest.raises(ValueError, match="Only"):
        build_annie_active({"champion_id": "TFT10_Olaf"})


@pytest.mark.parametrize("parameters", [[], [
    {"name": "MagicDamage", "value": [0, 220]},
    {"name": "MagicDamage", "value": [0, 220]},
]])
def test_missing_or_ambiguous_parameter(parameters):
    # 源数据缺失或重名不能静默挑一个值。
    with pytest.raises(ValueError, match="exactly one"):
        build_annie_active({"champion_id": "TFT10_Annie", "variables": parameters})


@pytest.mark.parametrize("damage", [-1, float("nan"), float("inf")])
def test_invalid_damage(fighter, damage):
    # 技能输入与普通攻击保持相同的有限非负要求。
    with pytest.raises(ValueError):
        ability_for(fighter, damage)


def test_cast_uses_mr_and_spends_mana(fighter):
    # 高护甲不影响魔法伤害；100魔抗将人工技能100减到50。
    target = replace(fighter, armor=999, magic_resist=100)
    result = run_duel(fighter, target, max_duration=4, mana_rules=ManaRules(10), ability_a=ability_for(fighter))
    casts = [e for e in result.events if e.event_type == "ability_cast"]
    assert [e.time for e in casts] == [2, 4]
    assert all(e.damage == 50 and e.raw_damage == 100 for e in casts)
    assert all(e.mana_change == -20 and e.mana_a == 0 for e in casts)
    assert all(not e.is_critical and e.critical_roll is None for e in casts)
    assert result.ability_casts_a == 2 and result.ability_casts_b == 0


def test_no_cast_below_threshold(fighter):
    # 未满蓝前不提前释放技能。
    result = run_duel(fighter, fighter, max_duration=1, mana_rules=ManaRules(10), ability_a=ability_for(fighter))
    assert result.ability_casts_a == 0


def test_initial_full_mana_can_cast_at_zero(fighter):
    # 即使窗口为0秒，已满蓝技能也属于窗口内的事件。
    full = replace(fighter, initial_mana=20)
    result = run_duel(full, fighter, max_duration=0, mana_rules=ManaRules(10), ability_a=ability_for(full))
    assert result.ability_casts_a == 1 and result.attacks_a == 0
    assert result.hp_b == 900 and result.duration == 0


def test_simultaneous_spell_double_ko(fighter):
    # 同刻技能全部确定后才扣血，不因处理A在前而取消B施法。
    full = replace(fighter, initial_mana=20)
    result = run_duel(full, full, mana_rules=ManaRules(10), ability_a=ability_for(full, 2000), ability_b=ability_for(full, 2000))
    assert result.reason == "double_ko"
    assert result.ability_casts_a == result.ability_casts_b == 1
    assert result.damage_a == result.damage_b == 1000
    assert all(e.hp_a == e.hp_b == 0 for e in result.events if e.event_type == "ability_cast")


def test_death_in_attack_phase_prevents_cast(fighter):
    # 本模型普攻阶段优先；同刻普攻已造成死亡时不再进入技能阶段。
    fragile = replace(fighter, max_hp=1, max_mana=10)
    result = run_duel(fragile, fighter, mana_rules=ManaRules(10), ability_a=ability_for(fragile))
    assert result.winner == "B" and result.ability_casts_a == 0


def test_survivor_does_not_cast_on_dead_target(fighter):
    # 对手被本次普攻击杀，即使自己刚满蓝也不计空放。
    target = replace(fighter, max_hp=1)
    attacker = replace(fighter, max_mana=10)
    result = run_duel(attacker, target, mana_rules=ManaRules(10), ability_a=ability_for(attacker))
    assert result.winner == "A" and result.ability_casts_a == 0


@pytest.mark.parametrize("change", [{"version_id": 2}, {"champion_id": "WRONG"}])
def test_identity_mismatch(fighter, change):
    # 不同源版本或英雄的技能配置不得混用。
    skill = replace(ability_for(fighter), **change)
    with pytest.raises(ValueError, match="does not match"):
        run_duel(fighter, fighter, mana_rules=ManaRules(10), ability_a=skill)


def test_cast_requires_positive_mana_and_explicit_rules(fighter):
    # 无法力槽单位不能进入无限瞬发循环。
    with pytest.raises(ValueError, match="requires"):
        run_duel(fighter, fighter, ability_a=ability_for(fighter))
    zero = replace(fighter, max_mana=0)
    with pytest.raises(ValueError, match="requires"):
        run_duel(zero, fighter, mana_rules=ManaRules(10), ability_a=ability_for(zero))


def test_skill_events_count_toward_resource_limit(fighter):
    # 普攻加技能共同消耗事件预算；不足时抛错而非返回假平局。
    with pytest.raises(RuntimeError, match="Combat-event"):
        run_duel(fighter, fighter, max_duration=2, max_events=4, mana_rules=ManaRules(10), ability_a=ability_for(fighter))


def test_skill_replay_and_input_isolation(fighter):
    # 重放时创建新状态，不把上场的法力、生命或技能次数带入下一场。
    arguments = dict(enable_crit=True, seed=42, mana_rules=ManaRules(10), ability_a=ability_for(fighter))
    first = run_duel(fighter, fighter, **arguments)
    assert first == run_duel(fighter, fighter, **arguments)
    assert fighter.initial_mana == 0 and fighter.max_hp == 1000
    assert first.metadata["skill_status"] == ["simplified_active_only", "not_modeled"]


def test_a_and_b_skills_can_cast_after_different_attacks(fighter):
    # 不同攻速的双方独立积累法力，技能不会重置普通攻击排期。
    fast = replace(fighter, attack_speed=2)
    result = run_duel(fighter, fast, max_duration=3, mana_rules=ManaRules(10), ability_a=ability_for(fighter, 1), ability_b=ability_for(fast, 1))
    assert result.attacks_a == 3 and result.attacks_b == 6
    assert result.ability_casts_a == 1 and result.ability_casts_b == 3
