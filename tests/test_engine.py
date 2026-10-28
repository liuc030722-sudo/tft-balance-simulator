"""Deterministic duel tests with explicitly synthetic champion fixtures."""

from dataclasses import replace

import pytest

from tft_simulator.combat.engine import run_duel
from tft_simulator.combat.timing import TimingRules
from tft_simulator.models import ChampionStats


@pytest.fixture
def fighter():
    # 人工夹具用于隔离验证引擎，不是真实英雄属性。
    return ChampionStats(
        version_id=1, champion_id="TEST_FIGHTER", name="Test fighter",
        max_hp=100.0, attack_damage=10.0, attack_speed=1.0,
        armor=0.0, magic_resist=0.0, attack_range=1.0,
        initial_mana=5.0, max_mana=50.0,
    )


def test_event_times_and_inclusive_timeout(fighter):
    # 1次/秒从t=1开始；截止t=2的攻击计入，存活双方按超时平局处理。
    result = run_duel(fighter, fighter, max_duration=2.0)
    attack_events = [e for e in result.events if e.event_type == "attack"]
    assert [e.time for e in attack_events] == [1.0, 1.0, 2.0, 2.0]
    assert result.winner == "draw" and result.reason == "timeout"
    assert result.duration == 2.0
    assert result.hp_a == result.hp_b == 80.0


def test_simultaneous_lethal_hits_are_draw(fighter):
    # 同时致命攻击必须双杀，而非循环中先处理的一方获胜。
    lethal = replace(fighter, attack_damage=100.0)
    result = run_duel(lethal, lethal)
    assert result.winner == "draw" and result.reason == "double_ko"
    assert result.hp_a == result.hp_b == 0.0
    assert result.attacks_a == result.attacks_b == 1
    attacks = [e for e in result.events if e.event_type == "attack"]
    assert all(e.hp_a == 0.0 and e.hp_b == 0.0 for e in attacks)
    assert len([e for e in result.events if e.event_type == "death"]) == 2


def test_death_cancels_future_attacks(fighter):
    # 更快的一方在0.5秒击杀，对手原定1秒的攻击不得继续发生。
    fast = replace(fighter, attack_speed=2.0, attack_damage=100.0)
    result = run_duel(fast, fighter)
    assert result.winner == "A" and result.reason == "death"
    assert result.duration == 0.5
    assert result.attacks_a == 1 and result.attacks_b == 0
    assert all(e.time <= 0.5 for e in result.events)


def test_swapping_sides_does_not_create_first_actor_advantage(fighter):
    # 交换双方后胜者身份应保持一致，仅位置编号变化。
    strong = replace(fighter, name="Strong fixture", attack_damage=100.0)
    left = run_duel(strong, fighter)
    right = run_duel(fighter, strong)
    assert left.winner == "A" and right.winner == "B"
    assert left.winner_name == right.winner_name == "Strong fixture"
    assert left.duration == right.duration
    assert left.hp_a == right.hp_b


def test_kill_at_deadline_has_priority_over_timeout(fighter):
    # 截止时刻的致命攻击先结算，然后才判断是否超时。
    lethal = replace(fighter, attack_damage=100.0)
    assert run_duel(lethal, fighter, max_duration=1.0).winner == "A"
    before = run_duel(lethal, fighter, max_duration=0.999)
    assert before.winner == "draw" and before.attacks_a == 0


def test_zero_duration_has_only_start_and_end(fighter):
    # 没有免费起手攻击，零时间窗口内不会发生伤害。
    result = run_duel(fighter, fighter, max_duration=0.0)
    assert result.duration == 0.0
    assert result.hp_a == result.hp_b == 100.0
    assert [e.event_type for e in result.events] == ["battle_start", "battle_end"]


def test_overkill_counts_only_removed_hp(fighter):
    # 伤害日志同时保留过量结算伤害和实际生命损失，摘要只累加后者。
    fast = replace(fighter, attack_speed=2.0, attack_damage=1000.0)
    result = run_duel(fast, fighter)
    hit = next(e for e in result.events if e.event_type == "attack")
    assert hit.damage_after_resistance == 1000.0
    assert hit.damage == result.damage_a == 100.0


def test_same_inputs_are_reproducible_and_do_not_mutate_stats(fighter):
    # 当前没有随机机制，不需要种子；重复输入必须得到相同日志和结果。
    assert run_duel(fighter, fighter) == run_duel(fighter, fighter)
    assert fighter.max_hp == 100.0
    assert run_duel(fighter, fighter).metadata["randomness"] == "none"


def test_mana_stays_constant_without_skill_system(fighter):
    # 没有实现法力系统时日志不能假装产生法力或释放技能。
    result = run_duel(fighter, fighter)
    assert all(e.mana_a == 5.0 and e.mana_b == 5.0 for e in result.events)


def test_optional_speed_cap_is_applied(fighter):
    # 自定义上限仅为测试规则，不称为官方Patch限制。
    fast = replace(fighter, attack_speed=2.0)
    result = run_duel(
        fast, fighter, max_duration=1.0, timing_rules=TimingRules(max_attack_speed=1.0),
    )
    assert result.attacks_a == result.attacks_b == 1


def test_resource_limit_is_error_not_draw(fighter):
    # 资源上限不能被包装成战斗超时或游戏平局。
    with pytest.raises(RuntimeError, match="event limit"):
        run_duel(fighter, fighter, max_events=1)


def test_versions_must_match(fighter):
    # 防止在未声明的情况下跨版本比较。
    with pytest.raises(ValueError, match="same source version"):
        run_duel(fighter, replace(fighter, version_id=2))


@pytest.mark.parametrize("duration", [-1.0, float("nan"), float("inf")])
def test_invalid_duration(fighter, duration):
    # 非法窗口在创建事件之前拒绝。
    with pytest.raises(ValueError):
        run_duel(fighter, fighter, max_duration=duration)


@pytest.mark.parametrize("limit", [0, -1, 1.5])
def test_invalid_event_limit(fighter, limit):
    # 事件数量限制必须为正整数。
    with pytest.raises(ValueError):
        run_duel(fighter, fighter, max_events=limit)


def test_damage_uses_armor_not_mr_and_logs_are_ordered(fighter):
    # 高魔抗不减少普通物理攻击；日志必须按时间排序并以结果结束。
    target = replace(fighter, armor=100.0, magic_resist=999.0, attack_damage=0.0)
    attacker = replace(fighter, attack_damage=100.0)
    result = run_duel(attacker, target)
    assert result.duration == 2.0 and result.winner == "A"
    assert result.damage_a == 100.0
    times = [e.time for e in result.events]
    assert times == sorted(times)
    assert result.events[-1].event_type == "battle_end"
    assert result.hp_a >= 0 and result.hp_b >= 0
