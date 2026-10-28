"""Combat calculations; full event simulation is not implemented yet."""

# Notebook通过这个入口调用正式函数；公式假设见docs/combat-mechanics.md。
from tft_simulator.combat.damage import magic_damage, physical_damage, true_damage
from tft_simulator.combat.timing import TimingRules, attack_interval, attack_times

__all__ = [
    "physical_damage", "magic_damage", "true_damage",
    "TimingRules", "attack_interval", "attack_times",
]
