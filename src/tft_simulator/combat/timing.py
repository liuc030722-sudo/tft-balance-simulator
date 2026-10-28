"""Fixed-rate attack timing with explicit, provisional rule configuration."""

import math
from dataclasses import dataclass

# 模型规则不是已核验的Patch 14.1客户端时间实现。
TIMING_MODEL_VERSION = "fixed_rate_v0.1_unverified"
_MAX_TIMELINE_EVENTS = 100_000


@dataclass(frozen=True)
class TimingRules:
    # 默认不猜测游戏攻速上下限；核验后可显式传入版本对应的限制。
    min_attack_speed: float | None = None
    max_attack_speed: float | None = None

    def __post_init__(self) -> None:
        # None表示不设置该限制，不等于零攻速。
        for value in (self.min_attack_speed, self.max_attack_speed):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError("Configured attack-speed limits must be finite and positive")
        if (
            self.min_attack_speed is not None and self.max_attack_speed is not None
            and self.min_attack_speed > self.max_attack_speed
        ):
            raise ValueError("Minimum attack speed cannot exceed maximum")


def effective_attack_speed(
    attack_speed: float, *, rules: TimingRules | None = None,
) -> float:
    # 输入单位是每秒攻击次数；只在显式配置时才应用上下限。
    if not math.isfinite(attack_speed) or attack_speed <= 0:
        raise ValueError("Attack speed must be finite and positive")
    speed = float(attack_speed)
    if rules is not None:
        if rules.min_attack_speed is not None:
            speed = max(speed, rules.min_attack_speed)
        if rules.max_attack_speed is not None:
            speed = min(speed, rules.max_attack_speed)
    if not math.isfinite(1.0 / speed):
        raise ValueError("Attack interval exceeds finite float range")
    return speed


def attack_interval(
    attack_speed: float, *, rules: TimingRules | None = None,
) -> float:
    # 间隔（秒/次）=1÷攻速（次/秒）；保留完整浮点精度。
    return 1.0 / effective_attack_speed(attack_speed, rules=rules)


def attack_times(
    attack_speed: float, duration: float, *, rules: TimingRules | None = None,
) -> list[float]:
    # 本模型第一击在第一个完整间隔后发生；包含恰好位于截止时刻的攻击。
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("Duration must be finite and nonnegative")
    speed = effective_attack_speed(attack_speed, rules=rules)
    estimated_count = duration * speed
    if not math.isfinite(estimated_count) or estimated_count > _MAX_TIMELINE_EVENTS:
        # 这是演示函数的内存保护，不是游戏中的攻击次数或攻速上限。
        raise ValueError("Timeline exceeds 100000 events; use a shorter duration")
    result: list[float] = []
    # 多检查一个候选，最终以绝对时间为准，避免乘法在整数边界处的舍入漏算。
    for attack_number in range(1, math.floor(estimated_count) + 2):
        event_time = attack_number / speed
        if event_time > duration:
            break
        result.append(event_time)
    return result
