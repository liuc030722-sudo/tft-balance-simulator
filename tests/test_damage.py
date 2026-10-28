"""Mathematical consistency tests for the documented provisional model."""

import pytest

from tft_simulator.combat import magic_damage, physical_damage, true_damage
from tft_simulator.combat.damage import resistance_multiplier
from tft_simulator.models import ChampionStats, CombatState


@pytest.mark.parametrize("resistance, multiplier", [
    (0.0, 1.0), (100.0, 0.5), (200.0, 1 / 3),
    (-50.0, 4 / 3), (-100.0, 1.5),
])
def test_resistance_formula(resistance, multiplier):
    # 核对暂定模型的数学结果，不表示这些值已通过实际TFT客户端验证。
    assert resistance_multiplier(resistance) == pytest.approx(multiplier)


@pytest.mark.parametrize("function", [physical_damage, magic_damage])
def test_typed_damage_and_precision(function):
    # 两种伤害都使用各自传入的抗性，并保留非整数结算结果。
    assert function(100.0, 100.0) == pytest.approx(50.0)
    assert function(40.0, 35.0) == pytest.approx(29.62962962962963)
    assert function(0.0, 35.0) == 0.0


def test_true_damage_bypasses_resistance_calculation():
    # 真实伤害接口没有抗性参数，输出为未修改的原始值。
    assert true_damage(123.45) == 123.45
    assert true_damage(0.0) == 0.0


@pytest.mark.parametrize("amount", [-1.0, float("nan"), float("inf")])
@pytest.mark.parametrize("kind", ["physical", "magic", "true"])
def test_invalid_raw_damage(kind, amount):
    # 三类伤害都必须拒绝非法原始输入。
    with pytest.raises(ValueError):
        if kind == "true":
            true_damage(amount)
        elif kind == "physical":
            physical_damage(amount, 0.0)
        else:
            magic_damage(amount, 0.0)


@pytest.mark.parametrize("resistance", [float("nan"), float("inf"), -float("inf")])
def test_invalid_resistance(resistance):
    # 非有限抗性不能被当作完全免伤或其他有效结算。
    with pytest.raises(ValueError):
        physical_damage(100.0, resistance)


def test_resistance_is_monotone_and_continuous_near_zero():
    # 更多抗性不得增加受到的伤害；零点两侧不应出现明显跳变。
    values = [resistance_multiplier(r) for r in [-100, -50, 0, 50, 100, 200]]
    assert values == sorted(values, reverse=True)
    assert resistance_multiplier(-1e-9) == pytest.approx(1.0)
    assert resistance_multiplier(1e-9) == pytest.approx(1.0)


def test_float_overflow_is_rejected():
    # 即使两个输入有限，乘积仍可能溢出；不能把无穷大传入状态对象。
    with pytest.raises(ValueError, match="finite float"):
        physical_damage(1.7e308, -100.0)


def test_damage_integrates_with_battle_state():
    # 人工夹具仅验证调用链：减伤计算→实际扣血，不代表真实英雄。
    stats = ChampionStats(
        version_id=1, champion_id="TEST_DAMAGE", name="Synthetic fixture",
        max_hp=100.0, attack_damage=10.0, attack_speed=1.0,
        armor=100.0, magic_resist=0.0, attack_range=1.0,
        initial_mana=0.0, max_mana=10.0,
    )
    state = CombatState(stats)
    assert state.take_damage(physical_damage(100.0, stats.armor)) == 50.0
    assert state.current_hp == 50.0
    assert state.take_damage(magic_damage(100.0, stats.magic_resist)) == 50.0
    assert state.current_hp == 0.0
    assert not state.is_alive
    assert stats.max_hp == 100.0
