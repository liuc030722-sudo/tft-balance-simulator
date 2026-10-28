"""Profile composition and declared support use artificial source fixtures."""

from dataclasses import replace
from unittest.mock import Mock, patch

import pytest

from tft_simulator.combat.profiles import build_profile, run_matchup
from tft_simulator.database.combatants import load_combatant


@pytest.fixture
def records():
    # 人工源夹具仅验证接口装配；不当作真实英雄统计或来源记录发布。
    version = dict(version_id=1, set_number=10, patch="14.1", source_url="https://example.invalid/test",
                   source_sha256="TEST_ONLY", retrieved_at_utc="2026-01-01T00:00:00+00:00")
    champion = dict(version_id=1, champion_id="TFT10_Annie", name="Fixture", hp=1000,
                    attack_damage=10, attack_speed=1, armor=0, magic_resist=0,
                    attack_range=1, initial_mana=0, max_mana=20, crit_chance=0.25, crit_multiplier=1.4)
    ability = dict(version_id=1, champion_id="TFT10_Annie", ability_name="Test active",
                   variables=[{"name": "MagicDamage", "value": [0, 100]}])
    return champion, version, ability


def test_explicit_baseline_has_no_skills(records):
    # 默认模式明确关闭技能，不悄悄声称已实现完整英雄。
    profile = build_profile(*records)
    assert profile.ability is None and profile.passive is None
    assert profile.skill_status == "disabled_by_request"
    assert profile.description()["omitted"] == "all_skills_and_passives"


def test_annie_profile_and_source_metadata(records):
    # 构造主动模型，并把缺失被动和来源说明带入结果。
    profile = build_profile(*records, enable_skills=True)
    result = run_matchup(profile, profile, mana_per_attack=10, enable_crit=True, seed=42)
    assert profile.ability.raw_damage == 100
    assert "empowered_passive" in profile.omitted
    assert result.metadata["source_snapshot"]["source_sha256"] == "TEST_ONLY"
    assert result.metadata["profiles"][0]["skill_status"] == "simplified_active_only"
    assert result == run_matchup(profile, profile, mana_per_attack=10, enable_crit=True, seed=42)


def test_olaf_profile_builds_passive(records):
    # 零法力槽仍能装配回血和动态攻速被动。
    champion, version, ability = records
    champion = dict(champion, champion_id="TFT10_Olaf", max_mana=0)
    ability = dict(ability, champion_id="TFT10_Olaf", variables=[
        {"name": "HealValue", "value": [0, 20]},
        {"name": "BonusAttackSpeed", "value": [0.0015, 0.0015]},
        {"name": "PercentMissingHealth", "value": [1, 1]},
    ])
    profile = build_profile(champion, version, ability, enable_skills=True)
    assert profile.ability is None and profile.passive.heal_per_attack == 20
    assert profile.passive.bonus_attack_speed_per_step == 0.0015


@pytest.mark.parametrize("version_changes", [{"set_number": 9}, {"patch": "14.2"}])
def test_skill_version_gate(records, version_changes):
    # 不让14.1的已声明模型自动套到其他Patch或Set。
    champion, version, ability = records
    with pytest.raises(NotImplementedError, match="14.1"):
        build_profile(champion, dict(version, **version_changes), ability, enable_skills=True)


def test_unsupported_skill_does_not_silently_fall_back(records):
    # 未支持英雄可以显式普攻实验，但开启技能时必须清楚报错。
    champion, version, ability = records
    champion = dict(champion, champion_id="TFT10_Ahri")
    with pytest.raises(NotImplementedError, match="unsupported"):
        build_profile(champion, version, ability, enable_skills=True)
    assert build_profile(champion, version).skill_status == "disabled_by_request"


@pytest.mark.parametrize("ability_changes", [{"version_id": 2}, {"champion_id": "TFT10_Olaf"}])
def test_wrong_ability_record_rejected(records, ability_changes):
    # 不能因为字段结构相同就混用不同英雄或版本的技能记录。
    champion, version, ability = records
    with pytest.raises(ValueError, match="do not match"):
        build_profile(champion, version, dict(ability, **ability_changes), enable_skills=True)


def test_missing_source_ability_rejected(records):
    # 缺失技能不填造默认伤害。
    champion, version, _ = records
    with pytest.raises(ValueError, match="required"):
        build_profile(champion, version, enable_skills=True)


def test_wrong_champion_version_and_nonboolean_mode(records):
    # 构造边界拒绝版本不一致或含糊的模式值。
    champion, version, ability = records
    with pytest.raises(ValueError, match="source version"):
        build_profile(champion, dict(version, version_id=2), ability)
    with pytest.raises(ValueError, match="boolean"):
        build_profile(*records, enable_skills="yes")


def test_mismatching_snapshots_rejected(records):
    # 即使版本ID相同，不同内容哈希也不进入同一场实验。
    profile = build_profile(*records)
    with pytest.raises(ValueError, match="same source snapshot"):
        run_matchup(profile, replace(profile, source_sha256="OTHER_TEST_ONLY"))


def test_mana_is_still_explicit(records):
    # 统一入口不隐藏或默认猜测每击回蓝量。
    profile = build_profile(*records, enable_skills=True)
    with pytest.raises(ValueError, match="explicit mana_rules"):
        run_matchup(profile, profile)


def test_loader_reads_without_mutation(records):
    # 模拟已有查询函数，验证编排层只读取并正确传递记录。
    champion, version, ability = records
    connection = Mock()
    with patch("tft_simulator.database.combatants.list_versions", return_value=[version]), \
         patch("tft_simulator.database.combatants.get_champion", return_value=champion), \
         patch("tft_simulator.database.combatants.get_ability", return_value=ability) as query:
        profile = load_combatant(connection, 1, "TFT10_Annie", enable_skills=True)
        assert profile.skill_status == "simplified_active_only"
        query.assert_called_once_with(connection, 1, "TFT10_Annie")


def test_loader_missing_champion(records):
    # 找不到英雄时立即说明，不生成空白或虚构英雄。
    with patch("tft_simulator.database.combatants.list_versions", return_value=[records[1]]), \
         patch("tft_simulator.database.combatants.get_champion", return_value=None):
        with pytest.raises(ValueError, match="not found"):
            load_combatant(Mock(), 1, "MISSING")
