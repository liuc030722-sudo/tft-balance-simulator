# Champion dataset dictionary — schema 1.0

Scope: the 15-champion Set 10 / patch 14.1 exploratory cohort. One row represents one selected champion's unmodified source attributes. No star-level derivation, equipment, traits, Headliner bonus, or battle state is applied. Base-stat star semantics still require separate verification before generating star-specific rows.

Source path prefix: `sets["10"].champions[]` in the raw CommunityDragon snapshot. The full raw-byte SHA-256 identifies the exact input. The user completed a simplified CSV export; exact round-trip validation and a separate export manifest were explicitly deferred.

| Column | In-memory type | Source / meaning |
|---|---|---|
| champion_id | text | `apiName`; stable source identifier within this version |
| name | text | `name`; English source display name |
| cost | Int64 | `cost`; source gold cost, 1–5 in this cohort |
| traits | list of text | `traits`; raw trait names; in-memory representation only |
| traits_json | text | CSV replacement for `traits`; JSON array, parsed with `json.loads` |
| role_raw | text | `role`; source role tag, distinct from traits and not a verified skill implementation |
| hp | Float64 | `stats.hp`; source health value |
| attack_damage | Float64 | `stats.damage`; source attack damage |
| attack_speed | Float64 | `stats.attackSpeed`; source attack-speed value; application rules still require verification |
| armor | Float64 | `stats.armor`; raw armor |
| magic_resist | Float64 | `stats.magicResist`; raw magic resistance |
| attack_range | Float64 | `stats.range`; raw range value; geometry and special values require verification |
| initial_mana | Float64 | `stats.initialMana`; starting mana, zero may be valid |
| max_mana | Float64 | `stats.mana`; source mana threshold, zero may be valid for passive units |
| crit_chance | Float64 | `stats.critChance`; probability-form source value, not percent text |
| crit_multiplier | Float64 | `stats.critMultiplier`; raw critical-hit multiplier; not percent text |
| set_number | integer | Acquisition manifest `set_number`, 10 |
| patch | text | Acquisition manifest `patch_directory`, `14.1`; preserve as text |
| source_url | text | Acquisition manifest `source_url` |
| retrieved_at_utc | text | ISO 8601 raw-data retrieval time with UTC offset |
| source_sha256 | text | Full SHA-256 of the original JSON bytes, not of the CSV |

## Export contract

- The current export path accepts only the validated, nonmissing 15-row cohort. If missing values appear, stop and design an explicit missing-value policy instead of silently filling or coercing them.
- Serialize trait lists using JSON, not Python list `repr`; keep the original DataFrame unchanged.
- CSV uses UTF-8 with BOM (`utf-8-sig`) and no DataFrame index. Do not round numeric columns or set a precision-reducing float format.
- CSV does not retain Python types. When loading it later, keep version fields as text and restore trait lists with `json.loads` where needed.
- Save timestamped filenames directly under `data/processed/`; do not silently overwrite earlier exports.
- Keep the existing source URL, retrieval time, and raw-file hash columns. Additional CSV hashes, exact readback checks, and an export manifest are not required in the current simplified workflow.
- A SHA-256 match establishes byte identity, not source correctness or fidelity of game mechanics.

## Known limitations

The cohort is purposively selected, three champions per cost. It is not representative of all Set 10 units. Sona's source range 16.0 is preserved pending semantic verification. Complete abilities, star scaling, equipment effects, and combat rules are not implemented. Inclusion in the dataset is not a support declaration for the battle engine.
