# Initial Set 10 / patch 14.1 cohort

Status: on 2026-10-28 the user supplied screenshots of the 15-row DataFrame and validation results: three champions per cost, no reported missing fields, and all eight listed basic checks passed. The user completed a simplified CSV export. The saved champion and ability CSV files each contain 15 records. Exact CSV round-trip validation was declined and is not required.

## Selection

Select exactly three champions from each cost, including source role tags covering tanks, fighters, and ranged casters/carries. This is a purposive exploratory cohort, not a random or representative sample of the whole set. Do not infer set-wide cost/performance relationships from this selection alone.

| Cost | Source API names |
|---|---|
| 1 | TFT10_Annie, TFT10_Olaf, TFT10_TahmKench |
| 2 | TFT10_Jax, TFT10_Garen, TFT10_Senna |
| 3 | TFT10_Amumu, TFT10_Riven, TFT10_Vex |
| 4 | TFT10_Ahri, TFT10_Ezreal, TFT10_Blitzcrank |
| 5 | TFT10_Jhin, TFT10_Sona, TFT10_Yorick |

Explicit IDs exclude summons and other special records without guessing that an ID prefix or a cost between 1 and 5 is sufficient. Verify each ID occurs exactly once. Save an exclusion ledger when building a comprehensive playable roster later; do not call all other records non-champions.

## Field handling

- `stats.damage` becomes `attack_damage`; `attackSpeed` becomes `attack_speed`; `magicResist` becomes `magic_resist`; `initialMana` becomes `initial_mana`; `mana` becomes `max_mana`; `range` becomes `attack_range`.
- Keep source numeric precision. Do not add star-level scaling or label generated higher-star values as source data.
- Preserve `traits` as a list. Preserve `role` as `role_raw`, a source classification separate from traits.
- Missing values stay missing. Do not fill them with zero. Zero mana can be valid for passive abilities.
- Preserve source, patch, Set, and full raw-file SHA-256 as provenance.
- Sona's raw range is 16.0 in this snapshot. Retain it and flag its semantics for later verification; do not cap it as a cleaning operation.
- Inclusion in a data table does not imply ability implementation. Multi-form abilities, summons, passive skills, and special attack rules must later be marked supported, simplified, or unsupported.

## Current step boundary

Acquisition, normalization, basic validation, and simplified export are complete for this cohort. See `model-scope.md` for the reduced first version and deferred mechanics. No PostgreSQL write is performed. No `.ipynb` file is created, edited, deleted, or executed by the agent. Phase 2 has not established complete skill execution or star-scaling semantics.
