"""State-model tests using synthetic fixtures, not TFT champion claims."""

from dataclasses import FrozenInstanceError

import pytest

from tft_simulator.models import ChampionStats, CombatState


@pytest.fixture
def record():
    # 人工测试夹具用于验证对象行为，不代表真实游戏英雄。
    return {
        "version_id": 1, "champion_id": "TEST_MODEL", "name": "Test fixture",
        "hp": 100.0, "attack_damage": 10.0, "attack_speed": 0.5,
        "armor": 10.0, "magic_resist": 10.0, "attack_range": 1.0,
        "initial_mana": 5.0, "max_mana": 50.0,
        "crit_chance": 0.0, "crit_multiplier": 1.0,
    }


def test_source_stats_are_immutable(record):
    # 防止战斗过程意外覆盖基础属性。
    stats = ChampionStats.from_record(record)
    with pytest.raises(FrozenInstanceError):
        stats.max_hp = 20.0


def test_input_record_is_not_retained_as_mutable_state(record):
    # 转换后不依赖输入字典的后续修改。
    stats = ChampionStats.from_record(record)
    record["hp"] = 1.0
    assert stats.max_hp == 100.0


def test_battles_have_independent_states(record):
    # 同一英雄可用于多场战斗，上一场扣血不能影响下一场。
    stats = ChampionStats.from_record(record)
    first = CombatState(stats)
    second = CombatState(stats)
    assert first.take_damage(30.0) == 30.0
    assert first.current_hp == 70.0
    assert second.current_hp == 100.0
    assert stats.max_hp == 100.0
    assert record["hp"] == 100.0
    assert first.current_mana == 5.0


def test_overkill_and_death(record):
    # 过量伤害只记实际扣血，生命值不为负，死亡后不再扣血。
    state = CombatState(ChampionStats.from_record(record))
    assert state.take_damage(1000.0) == 100.0
    assert state.current_hp == 0.0
    assert not state.is_alive
    assert state.take_damage(10.0) == 0.0


@pytest.mark.parametrize("amount", [-1.0, float("nan"), float("inf")])
def test_invalid_damage_does_not_change_state(record, amount):
    # 非法伤害不能污染状态。
    state = CombatState(ChampionStats.from_record(record))
    with pytest.raises(ValueError):
        state.take_damage(amount)
    assert state.current_hp == 100.0


@pytest.mark.parametrize("changes", [
    {"hp": 0.0}, {"attack_speed": 0.0}, {"hp": float("nan")},
    {"initial_mana": 51.0}, {"attack_damage": -1.0},
])
def test_invalid_source_stats_are_rejected(record, changes):
    # 在模型入口阻止无效属性，不额外假定版本相关的攻速上限。
    with pytest.raises(ValueError):
        ChampionStats.from_record({**record, **changes})


@pytest.mark.parametrize("changes", [
    {"crit_chance": -0.1}, {"crit_chance": 1.1}, {"crit_chance": float("nan")},
    {"crit_multiplier": 0.5}, {"crit_multiplier": float("inf")},
])
def test_invalid_critical_source_stats(record, changes):
    # 源字段语义限制与当前独立逐击暴击模型一致，不虚构额外转换规则。
    with pytest.raises(ValueError):
        ChampionStats.from_record({**record, **changes})


def test_missing_database_critical_field_is_not_filled(record):
    # 直接构造对象的测试默认值不能被用来补造缺失的真实数据库属性。
    del record["crit_chance"]
    with pytest.raises(KeyError):
        ChampionStats.from_record(record)
