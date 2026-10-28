"""Explicit combat profiles and a stable single-duel entry point."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from tft_simulator.combat.abilities import SimplifiedMagicAbility, build_annie_active
from tft_simulator.combat.engine import BattleResult, run_duel
from tft_simulator.combat.mana import ManaRules
from tft_simulator.combat.modifiers import ABILITY_POWER_MODEL_VERSION, scale_ability_effects, validate_ability_power
from tft_simulator.combat.passives import AttackHealPassive, build_olaf_passive
from tft_simulator.combat.timing import TimingRules
from tft_simulator.models import ChampionStats


@dataclass(frozen=True)
class CombatantProfile:
    # 把源属性、显式技能配置和来源说明组合起来，不修改原始记录。
    stats: ChampionStats
    ability: SimplifiedMagicAbility | None
    passive: AttackHealPassive | None
    skill_status: str
    implemented: tuple[str, ...]
    omitted: tuple[str, ...]
    set_number: int
    patch: str
    source_url: str
    source_sha256: str
    retrieved_at: str
    ability_power_percent: float = 100.0

    def __post_init__(self) -> None:
        # 配置边界拒绝负法强和非有限实验值；不把它写入源ChampionStats。
        validate_ability_power(self.ability_power_percent)
        if self.ability_power_percent != 100 and self.ability is None and self.passive is None:
            raise ValueError("No modeled ability effects to scale; enable supported skills first")

    def description(self) -> dict[str, Any]:
        # 返回适合Notebook展示的简短信息，保留“未建模”的可见性。
        return {"name": self.stats.name, "champion_id": self.stats.champion_id,
                "set": self.set_number, "patch": self.patch,
                "skill_status": self.skill_status,
                "ability_power_percent": self.ability_power_percent,
                "implemented": "; ".join(self.implemented),
                "omitted": "; ".join(self.omitted)}


def build_profile(champion: Mapping[str, Any], version: Mapping[str, Any],
                  ability_record: Mapping[str, Any] | None = None, *,
                  enable_skills: bool = False) -> CombatantProfile:
    # 技能必须显式开启，未支持英雄绝不静默降级成“技能已实现”。
    if not isinstance(enable_skills, bool):
        raise ValueError("enable_skills must be boolean")
    stats = ChampionStats.from_record(champion)
    if stats.version_id != int(version["version_id"]):
        raise ValueError("Champion and source version do not match")
    active, passive = None, None
    status = "disabled_by_request"
    implemented = ("ordinary_attacks",)
    omitted = ("all_skills_and_passives",)
    if enable_skills:
        if int(version["set_number"]) != 10 or str(version["patch"]) != "14.1":
            raise NotImplementedError("Selected skills support only Set 10 / Patch 14.1")
        if stats.champion_id not in ("TFT10_Annie", "TFT10_Olaf"):
            raise NotImplementedError(f"Skill model unsupported: {stats.champion_id}; use enable_skills=False for an explicit attack baseline")
        if ability_record is None:
            raise ValueError("Source ability record is required")
        if (int(ability_record["version_id"]), ability_record["champion_id"]) != (stats.version_id, stats.champion_id):
            raise ValueError("Ability record and champion do not match")
        if stats.champion_id == "TFT10_Annie":
            active = build_annie_active(ability_record)
            status = "simplified_active_only"
            implemented += ("single_target_magic_active",)
            implemented += ("experimental_AP_effect_scaling",)
            omitted = ("empowered_passive", "bonus_attack_speed", "secondary_target_damage", "verified_client_AP_formula", "cast_animation_and_mana_lock")
        else:
            passive = build_olaf_passive(ability_record)
            status = "simplified_heal_and_missing_hp_speed"
            implemented += ("on_attack_healing", "missing_health_attack_speed")
            implemented += ("experimental_AP_effect_scaling",)
            omitted = ("verified_client_AP_formula", "client_animation_and_exact_effect_order")
    return CombatantProfile(
        stats, active, passive, status, implemented, omitted,
        int(version["set_number"]), str(version["patch"]),
        str(version["source_url"]), str(version["source_sha256"]),
        str(version["retrieved_at_utc"]),
    )


def with_ability_power(profile: CombatantProfile, *, percent: float) -> CombatantProfile:
    # 返回独立实验配置；源技能伤害/回血仍保留在原配置中，运行时才缩放。
    return replace(profile, ability_power_percent=percent)


def run_matchup(a: CombatantProfile, b: CombatantProfile, *,
                mana_per_attack: float | None = None,
                enable_crit: bool = False, seed: int | None = None,
                max_duration: float = 60.0, max_events: int = 100_000,
                timing_rules: TimingRules | None = None) -> BattleResult:
    # 统一入口仅装配已有引擎，不复制战斗算法；回蓝假设仍由调用者明确指定。
    if (a.stats.version_id, a.source_sha256) != (b.stats.version_id, b.source_sha256):
        raise ValueError("Combatants must share the same source snapshot")
    rules = ManaRules(mana_per_attack) if mana_per_attack is not None else None
    effects_a = scale_ability_effects(a.ability, a.passive, percent=a.ability_power_percent)
    effects_b = scale_ability_effects(b.ability, b.passive, percent=b.ability_power_percent)
    result = run_duel(
        a.stats, b.stats, ability_a=effects_a[0], ability_b=effects_b[0],
        passive_a=effects_a[1], passive_b=effects_b[1], mana_rules=rules,
        enable_crit=enable_crit, seed=seed, max_duration=max_duration,
        max_events=max_events, timing_rules=timing_rules,
    )
    # 将快照来源和显式支持范围带入结果，后续统计可辨认模型差异。
    result.metadata["profiles"] = [a.description(), b.description()]
    # 同时记录缩放前来源效果和实验百分数；引擎已有metadata保存实际使用的效果。
    result.metadata["ability_power_model"] = ABILITY_POWER_MODEL_VERSION
    result.metadata["ability_power_experiments"] = [
        {"percent": profile.ability_power_percent,
         "source_raw_damage": profile.ability.raw_damage if profile.ability else None,
         "source_heal_per_attack": profile.passive.heal_per_attack if profile.passive else None}
        for profile in (a, b)
    ]
    result.metadata["source_snapshot"] = {
        "set_number": a.set_number, "patch": a.patch,
        "source_url": a.source_url, "source_sha256": a.source_sha256,
        "retrieved_at": a.retrieved_at,
    }
    return result
