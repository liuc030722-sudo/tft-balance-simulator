"""Experimental AP scaling uses explicit artificial effect fixtures."""

from dataclasses import replace

import pytest

from tft_simulator.combat.abilities import SimplifiedMagicAbility
from tft_simulator.combat.modifiers import scale_ability_effects
from tft_simulator.combat.passives import AttackHealPassive
from tft_simulator.combat.profiles import build_profile, run_matchup, with_ability_power


@pytest.fixture
def profile():
    # 人工记录用于精确比较法强实验，不是新增真实英雄数据。
    champion = dict(version_id=1, champion_id="TFT10_Annie", name="AP fixture", hp=1000,
                    attack_damage=10, attack_speed=1, armor=0, magic_resist=0, attack_range=1,
                    initial_mana=0, max_mana=20, crit_chance=0.25, crit_multiplier=1.4)
    version = dict(version_id=1, set_number=10, patch="14.1", source_url="https://example.invalid/test",
                   source_sha256="TEST_ONLY", retrieved_at_utc="2026-01-01T00:00:00+00:00")
    skill = dict(version_id=1, champion_id="TFT10_Annie", ability_name="Test active",
                 variables=[{"name": "MagicDamage", "value": [0, 100]}])
    return build_profile(champion, version, skill, enable_skills=True)


@pytest.mark.parametrize("percent, expected", [(0, 0), (100, 220), (150, 330)])
def test_active_damage_scale(percent, expected):
    # 线性缩放原伤害；不改变身份、参数名或源索引。
    ability = SimplifiedMagicAbility(1, "TEST_ONLY", "Test", 220, "TestDamage", 1)
    scaled, _ = scale_ability_effects(ability, None, percent=percent)
    assert scaled.raw_damage == expected and ability.raw_damage == 220
    assert scaled.source_parameter == ability.source_parameter


def test_heal_scales_without_speed_scaling():
    # Olaf法强实验仅改变治疗，不把缺血攻速也乘1.5。
    passive = AttackHealPassive(1, "TEST_ONLY", "Test", 20, "TestHeal", 1, 0.0015, 1)
    _, scaled = scale_ability_effects(None, passive, percent=150)
    assert scaled.heal_per_attack == 30 and passive.heal_per_attack == 20
    assert scaled.bonus_attack_speed_per_step == 0.0015
    assert scaled.missing_health_percent_step == 1


@pytest.mark.parametrize("percent", [-1, float("inf"), float("nan"), True, "150"])
def test_invalid_ap(profile, percent):
    # 配置时就拒绝非法实验输入，不等到运行时污染战斗状态。
    with pytest.raises(ValueError):
        with_ability_power(profile, percent=percent)


def test_profile_configuration_is_not_compounded(profile):
    # 从150改到200，是源值的2倍而非150%结果再乘2倍。
    increased = with_ability_power(profile, percent=150)
    changed = with_ability_power(increased, percent=200)
    active, _ = scale_ability_effects(changed.ability, changed.passive, percent=changed.ability_power_percent)
    assert active.raw_damage == 200
    assert changed.ability.raw_damage == increased.ability.raw_damage == profile.ability.raw_damage == 100
    assert profile.ability_power_percent == 100


def test_scale_before_resistance_and_preserve_attack_stats(profile):
    # 100源伤害×150%=150，再过100魔抗得到75；AD保持10。
    target = replace(profile, stats=replace(profile.stats, magic_resist=100))
    boosted = with_ability_power(profile, percent=150)
    result = run_matchup(boosted, target, mana_per_attack=10, max_duration=2)
    cast = next(e for e in result.events if e.event_type == "ability_cast" and e.actor_side == "A")
    assert cast.raw_damage == 150 and cast.damage_after_resistance == 75
    attack = next(e for e in result.events if e.event_type == "attack" and e.actor_side == "A")
    assert attack.raw_damage == 10 and boosted.stats == profile.stats


def test_100_percent_preserves_existing_result(profile):
    # 默认配置和显式100%实验具有完全相同结果。
    explicit = with_ability_power(profile, percent=100)
    assert run_matchup(profile, profile, mana_per_attack=10) == run_matchup(explicit, profile, mana_per_attack=10)


def test_result_records_original_and_effective_values(profile):
    # 元数据必须区分原始参数与实验生效参数，便于以后复现实验。
    boosted = with_ability_power(profile, percent=150)
    result = run_matchup(boosted, profile, mana_per_attack=10, max_duration=2)
    assert result.metadata["ability_power_experiments"][0] == {
        "percent": 150, "source_raw_damage": 100, "source_heal_per_attack": None,
    }
    assert result.metadata["abilities"][0]["raw_damage"] == 150
    assert result.metadata["profiles"][0]["ability_power_percent"] == 150


def test_disabled_skills_do_not_accept_meaningless_ap(profile):
    # 技能关闭后没有可缩放效果，避免显示无实际意义的“法强已生效”。
    baseline = replace(profile, ability=None, passive=None)
    with pytest.raises(ValueError, match="No modeled"):
        with_ability_power(baseline, percent=150)
    with pytest.raises(ValueError, match="No modeled"):
        scale_ability_effects(None, None, percent=150)


def test_effect_overflow_rejected(profile):
    # 极端有限配置仍可能令乘积溢出，效果模型必须拒绝无穷伤害。
    huge = replace(profile.ability, raw_damage=1e308)
    with pytest.raises(ValueError, match="finite"):
        scale_ability_effects(huge, None, percent=1e308)


def test_seeded_ap_replay(profile):
    # 法强实验和暴击共存时仍可重放，不沿用上一场状态。
    boosted = with_ability_power(profile, percent=150)
    args = dict(mana_per_attack=10, enable_crit=True, seed=42)
    assert run_matchup(boosted, profile, **args) == run_matchup(boosted, profile, **args)
