"""Tests of the declared fixed-rate timing model, not client measurements."""

import pytest

from tft_simulator.combat import TimingRules, attack_interval, attack_times


@pytest.mark.parametrize("speed, expected", [(0.5, 2.0), (1.0, 1.0), (2.0, 0.5)])
def test_reciprocal_interval(speed, expected):
    # 核对秒/次与次/秒互为倒数。
    assert attack_interval(speed) == pytest.approx(expected)


@pytest.mark.parametrize("speed", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_speed_is_rejected(speed):
    # 不将零攻速错误解释为零间隔或立即无限攻击。
    with pytest.raises(ValueError):
        attack_interval(speed)


@pytest.mark.parametrize("speed, expected", [(0.1, 2.0), (1.0, 1.0), (10.0, 0.2)])
def test_explicit_bounds(speed, expected):
    # 0.5和5.0仅为测试配置，不声称它们是目标Patch的官方限制。
    rules = TimingRules(min_attack_speed=0.5, max_attack_speed=5.0)
    assert attack_interval(speed, rules=rules) == pytest.approx(expected)


def test_default_does_not_apply_unverified_game_cap():
    # 默认无上限截断，避免把未核验的版本规则写死。
    assert attack_interval(10.0) == pytest.approx(0.1)


def test_first_attack_and_inclusive_deadline():
    # 固定规则：不在t=0攻击，t=1的攻击在1秒窗口内计入。
    assert attack_times(2.0, duration=1.0) == [0.5, 1.0]
    assert attack_times(2.0, duration=0.0) == []
    assert attack_times(2.0, duration=0.99) == [0.5]


def test_absolute_times_avoid_repeated_addition_boundary_error():
    # n/AS的0.3秒事件应包含；不使用0.1+0.1+0.1反复累加。
    assert attack_times(10.0, duration=0.3) == [0.1, 0.2, 0.3]


def test_source_precision_is_preserved():
    # 来自源文件的攻速略小于0.7时，第七击略晚于10秒，不应提前算入。
    assert len(attack_times(0.699999988079071, duration=10.0)) == 6
    assert len(attack_times(0.7, duration=10.0)) == 7


@pytest.mark.parametrize("duration", [-1.0, float("nan"), float("inf")])
def test_invalid_duration(duration):
    # 非法时间窗口不能进入事件生成循环。
    with pytest.raises(ValueError):
        attack_times(1.0, duration)


@pytest.mark.parametrize("values", [
    {"min_attack_speed": 0.0}, {"max_attack_speed": -1.0},
    {"min_attack_speed": 2.0, "max_attack_speed": 1.0},
    {"min_attack_speed": float("nan")}, {"max_attack_speed": float("inf")},
])
def test_invalid_rule_configuration(values):
    # 版本参数自身也必须合法，不能把配置错误当作游戏行为。
    with pytest.raises(ValueError):
        TimingRules(**values)


def test_large_demo_timeline_is_rejected():
    # 仅验证演示列表的资源保护，不代表真实游戏攻击次数限制。
    with pytest.raises(ValueError, match="100000"):
        attack_times(1_000_000.0, duration=1.0)
