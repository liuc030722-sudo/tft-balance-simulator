"""Critical model and seeded engine tests; fixtures are synthetic."""

import random
from dataclasses import replace
from random import Random

import pytest

from tft_simulator.combat.critical import roll_critical_hit
from tft_simulator.combat.engine import run_duel
from tft_simulator.models import ChampionStats


@pytest.fixture
def fighter():
    # 人工夹具突出暴击逻辑，不声称这些是某个真实TFT英雄的属性。
    return ChampionStats(
        version_id=1, champion_id="TEST_CRIT", name="Critical test fixture",
        max_hp=100.0, attack_damage=10.0, attack_speed=1.0,
        armor=0.0, magic_resist=0.0, attack_range=1.0,
        initial_mana=0.0, max_mana=10.0, crit_chance=0.5, crit_multiplier=2.0,
    )


@pytest.mark.parametrize("chance, critical, damage", [(0.0, False, 100.0), (1.0, True, 140.0)])
def test_probability_endpoints(chance, critical, damage):
    # 0%绝不暴击，100%必定暴击；使用数学例子而非游戏结论。
    hit = roll_critical_hit(100.0, chance, 1.4, rng=Random(42))
    assert hit.is_critical is critical
    assert hit.raw_damage == pytest.approx(damage)
    assert 0 <= hit.roll < 1


def test_fixed_seed_threshold_and_replay():
    # 固定种子的前两个随机数跨过0.25阈值，验证逐击判定及可重放性。
    first_rng = Random(42)
    first = roll_critical_hit(40.0, 0.25, 1.4, rng=first_rng)
    second = roll_critical_hit(40.0, 0.25, 1.4, rng=first_rng)
    assert not first.is_critical and second.is_critical
    assert first.roll == pytest.approx(0.6394267984578837)
    assert second.raw_damage == pytest.approx(56.0)
    replay_rng = Random(42)
    assert first == roll_critical_hit(40.0, 0.25, 1.4, rng=replay_rng)
    assert second == roll_critical_hit(40.0, 0.25, 1.4, rng=replay_rng)


@pytest.mark.parametrize("values", [
    (-1.0, 0.25, 1.4), (100.0, -0.1, 1.4), (100.0, 1.1, 1.4),
    (100.0, 0.25, 0.5), (float("nan"), 0.25, 1.4),
    (100.0, float("inf"), 1.4), (100.0, 0.25, float("inf")),
])
def test_invalid_critical_inputs(values):
    # 未实现溢出暴击率规则，不悄悄截断错误输入。
    with pytest.raises(ValueError):
        roll_critical_hit(*values, rng=Random(42))


def test_critical_overflow_is_rejected():
    # 暴击乘积溢出时不允许无穷大进入抗性和扣血计算。
    with pytest.raises(ValueError, match="finite float"):
        roll_critical_hit(1.7e308, 1.0, 2.0, rng=Random(42))


def test_seed_reproduces_full_result_and_logs(fighter):
    # 同输入、同种子、同引擎版本必须返回相同结果和每次随机数。
    first = run_duel(fighter, fighter, enable_crit=True, seed=42)
    second = run_duel(fighter, fighter, enable_crit=True, seed=42)
    assert first == second
    assert first.metadata["random_seed"] == 42
    assert first.metadata["critical_strikes"] is True


def test_different_seeds_change_rolls_not_necessarily_winner(fighter):
    # 不要求不同种子一定改变胜负；先验证随机轨迹确实不同。
    first = run_duel(fighter, fighter, enable_crit=True, seed=42)
    second = run_duel(fighter, fighter, enable_crit=True, seed=2026)
    first_rolls = [event.critical_roll for event in first.events if event.event_type == "attack"]
    second_rolls = [event.critical_roll for event in second.events if event.event_type == "attack"]
    assert first_rolls != second_rolls


def test_local_rng_does_not_modify_global_state(fighter):
    # Notebook里其他代码的全局随机状态不应被战斗调用污染。
    before = random.getstate()
    run_duel(fighter, fighter, enable_crit=True, seed=42)
    assert random.getstate() == before


def test_critical_raw_damage_and_armor_in_log(fighter):
    # 日志必须可解释：基础AD40→暴击前抗性伤害60→100护甲后30。
    attacker = replace(fighter, attack_damage=40.0, crit_chance=1.0, crit_multiplier=1.5)
    defender = replace(fighter, armor=100.0, attack_damage=0.0)
    result = run_duel(attacker, defender, enable_crit=True, seed=42, max_duration=1.0)
    hit = next(event for event in result.events if event.actor_side == "A")
    assert hit.is_critical
    assert hit.base_attack_damage == 40.0
    assert hit.raw_damage == 60.0
    assert hit.damage_after_resistance == hit.damage == 30.0
    assert result.critical_hits_a == 1


def test_zero_probability_matches_baseline_damage(fighter):
    # 零暴击率即使启用掷骰，数值摘要也与无暴击基线一致。
    no_crit = replace(fighter, crit_chance=0.0)
    baseline = run_duel(no_crit, no_crit)
    seeded = run_duel(no_crit, no_crit, enable_crit=True, seed=42)
    assert baseline.summary() == seeded.summary()
    assert all(not event.is_critical for event in seeded.events)


def test_guaranteed_critical_double_ko(fighter):
    # 双方同刻的暴击都先确定，不因先扣血而取消另一方暴击。
    lethal = replace(fighter, attack_damage=50.0, crit_chance=1.0)
    result = run_duel(lethal, lethal, enable_crit=True, seed=42)
    assert result.reason == "double_ko"
    assert result.critical_hits_a == result.critical_hits_b == 1


@pytest.mark.parametrize("seed", [None, 1.5, True])
def test_critical_mode_requires_integer_seed(fighter, seed):
    # 强制显式种子，避免无法重放的隐式随机实验。
    with pytest.raises(ValueError, match="integer seed"):
        run_duel(fighter, fighter, enable_crit=True, seed=seed)


def test_disabled_mode_does_not_pretend_to_use_seed(fighter):
    # 关闭随机机制时拒绝无效种子，防止用户误以为结果受种子控制。
    with pytest.raises(ValueError, match="no effect"):
        run_duel(fighter, fighter, seed=42)


def test_baseline_logs_no_random_draws(fighter):
    # 默认入口保持Phase 4行为，日志不伪造随机数或暴击。
    result = run_duel(fighter, fighter)
    assert result.metadata["randomness"] == "none"
    assert result.critical_hits_a == result.critical_hits_b == 0
    assert all(event.critical_roll is None for event in result.events)
