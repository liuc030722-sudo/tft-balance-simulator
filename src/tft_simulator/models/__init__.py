"""Static champion attributes and per-battle state."""

# 对外提供统一导入入口；战斗公式和事件引擎将在后续步骤加入。
from tft_simulator.models.champion import ChampionStats, CombatState

__all__ = ["ChampionStats", "CombatState"]
