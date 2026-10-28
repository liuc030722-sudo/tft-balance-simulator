"""Artificial state and combat fixtures for partial healing passives."""

from dataclasses import replace

import pytest

from tft_simulator.combat.abilities import SimplifiedMagicAbility
from tft_simulator.combat.engine import run_duel
from tft_simulator.combat.mana import ManaRules
from tft_simulator.combat.passives import AttackHealPassive, build_olaf_healing
from tft_simulator.models import ChampionStats, CombatState


@pytest.fixture
def fighter():
    # 人工夹具用于精确计算治疗和时序，不代表真实TFT英雄。
    return ChampionStats(
        version_id=1, champion_id="TEST_HEAL", name="Heal fixture",
        max_hp=100, attack_damage=10, attack_speed=1,
        armor=0, magic_resist=0, attack_range=1, initial_mana=0, max_mana=10,
    )


def passive_for(stats, amount=20):
    # 底层配置允许人工测试；真实Olaf参数由源记录工厂提取。
    return AttackHealPassive(stats.version_id, stats.champion_id, "Test heal", amount, "TEST_ONLY", 1)


def test_healing_cap_and_return_value(fighter):
    # 实际治疗只能补充缺失生命；满血时不增加生命值。
    state = CombatState(fighter)
    assert state.heal(20) == 0
    state.take_damage(5)
    assert state.heal(20) == 5
    assert state.current_hp == 100


def test_dead_cannot_revive(fighter):
    # 普通治疗不能改变已死亡状态。
    state = CombatState(fighter)
    state.take_damage(100)
    assert state.heal(100) == 0
    assert not state.is_alive


@pytest.mark.parametrize("amount", [-1, float("inf"), float("nan")])
def test_invalid_healing(fighter, amount):
    # 非法治疗量在配置与状态边界都被拒绝。
    with pytest.raises(ValueError):
        CombatState(fighter).heal(amount)
    with pytest.raises(ValueError):
        passive_for(fighter, amount)


def test_factory_reads_source_parameter():
    # 测试提取过程，参数仍保留版本和索引，避免丢失来源语义。
    passive = build_olaf_healing({
        "version_id": 4, "champion_id": "TFT10_Olaf", "ability_name": "Berserker Rage",
        "variables": [{"name": "HealValue", "value": [0, 20, 25, 35]}],
    })
    assert passive.heal_per_attack == 20 and passive.version_id == 4
    assert passive.source_parameter == "HealValue" and passive.source_index == 1


def test_factory_rejects_other_champion_and_missing_parameter():
    # 不从其他英雄或缺失参数中猜测治疗量。
    with pytest.raises(ValueError, match="Only"):
        build_olaf_healing({"champion_id": "TFT10_Annie"})
    with pytest.raises(ValueError, match="exactly one"):
        build_olaf_healing({"champion_id": "TFT10_Olaf", "variables": []})


def test_partial_heal_counts_actual_not_requested(fighter):
    # 每轮受到10点伤害、请求治疗20，但实际治疗只有10。
    result = run_duel(fighter, fighter, max_duration=2, passive_b=passive_for(fighter))
    assert result.hp_b == 100 and result.healing_b == 20
    heals = [e for e in result.events if e.event_type == "heal"]
    assert len(heals) == 2 and all(e.healing == 10 and e.damage == 0 for e in heals)
    assert result.ability_casts_b == 0


def test_heal_before_cast_does_not_revive_after_spell(fighter):
    # 先普攻伤害90→被动治疗20至100→技能伤害100，最后仍死亡。
    skill = SimplifiedMagicAbility(1, fighter.champion_id, "Test magic", 100, "TEST_ONLY", 1)
    result = run_duel(fighter, fighter, mana_rules=ManaRules(10), ability_a=skill,
                      passive_b=passive_for(fighter), max_duration=1)
    assert result.winner == "A" and result.hp_b == 0
    kinds = [e.event_type for e in result.events]
    assert kinds.index("heal") < kinds.index("ability_cast") < kinds.index("death")
    assert result.healing_b == 10


def test_lethal_attack_prevents_heal(fighter):
    # 同刻致命普攻优先于治疗，不能靠被动复活。
    lethal = replace(fighter, attack_damage=100)
    result = run_duel(lethal, lethal, passive_a=passive_for(lethal), passive_b=passive_for(lethal))
    assert result.reason == "double_ko" and result.healing_a == result.healing_b == 0


def test_killing_attack_still_heals_survivor(fighter):
    # 普攻结束时对手死亡，不取消存活攻击者已经触发的回血。
    attacker = replace(fighter, attack_damage=100)
    result = run_duel(attacker, fighter, passive_a=passive_for(attacker))
    assert result.winner == "A" and result.hp_a == 100 and result.healing_a == 10


@pytest.mark.parametrize("change", [{"version_id": 2}, {"champion_id": "WRONG"}])
def test_passive_identity_mismatch(fighter, change):
    # 禁止跨版本或跨英雄装备被动配置。
    with pytest.raises(ValueError, match="does not match"):
        run_duel(fighter, fighter, passive_b=replace(passive_for(fighter), **change))


def test_zero_mana_unit_can_have_passive(fighter):
    # 被动不消耗法力，不依赖满蓝或回蓝配置。
    zero = replace(fighter, max_mana=0)
    result = run_duel(fighter, zero, max_duration=1, passive_b=passive_for(zero))
    assert result.healing_b == 10 and result.events[-1].mana_b == 0


def test_no_heal_events_at_full_health(fighter):
    # 对手不造成伤害时，不制造无变化的回血记录。
    harmless = replace(fighter, attack_damage=0)
    result = run_duel(harmless, fighter, max_duration=2, passive_b=passive_for(fighter))
    assert result.healing_b == 0
    assert not any(e.event_type == "heal" for e in result.events)


def test_replay_and_health_accounting(fighter):
    # 累计伤害与治疗共同解释剩余生命；每场状态独立，可重复运行。
    args = dict(max_duration=5, enable_crit=True, seed=42, passive_b=passive_for(fighter, 5))
    first = run_duel(fighter, fighter, **args)
    assert first == run_duel(fighter, fighter, **args)
    assert first.hp_b == pytest.approx(fighter.max_hp - first.damage_a + first.healing_b)
    assert first.metadata["passive_status"] == ["not_modeled", "partial_heal_only"]
    assert first.metadata["dynamic_attack_speed"] is False
