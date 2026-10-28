# Combat mechanics — provisional damage model

Model ID: `resistance_v0.1_unverified`.

## Evidence versus assumptions

Champion source attributes come from the archived CommunityDragon Set 10 / patch 14.1 snapshot. Riot's official patch notes can cross-check changed champion values, such as Olaf's AD becoming 55:

https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-14-1-notes/

That patch article is not a complete specification of resistance calculations. The source review did not establish a Riot-authored, Patch 14.1-specific specification for the full armor/MR formula, negative resistances, or rounding behavior. Consequently **both branches below are declared provisional model rules**, not certified Riot mechanics. Their tests establish mathematical correctness against this definition, not fidelity to the client. Do not promote this status to verified without additional primary evidence or a documented controlled measurement.

## Defined resistance multiplier

Let R be the resistance relevant to a damage instance:

```text
R >= 0: multiplier = 100 / (100 + R)
R <  0: multiplier = 2 - 100 / (100 - R)
```

The negative branch is a chosen continuous amplification extension. It avoids the singularity of applying the positive branch at R=-100 and is not claimed to be TFT's negative-resistance implementation. Neither penetration nor resistance-reduction mechanics are currently modeled.

- Physical: D = D0 × multiplier(armor).
- Magic: D = D0 × multiplier(magic_resist).
- True: D = D0; bypasses the two resistance terms in this model.

D0 is nonnegative pre-mitigation damage, D is damage after the resistance calculation. Examples: D0=100 and R=100 gives 50; D0=100 and R=-50 gives approximately 133.3333. True damage 100 returns 100 regardless of any unmodeled defensive effects.

The notebook's plain-attack example sets D0 to source attack_damage, with critical strikes, passives, attack modifiers, shields, damage reduction, and abilities disabled. It is a standardized baseline and must not be described as the full attack behavior of every TFT champion.

## State application and precision

- Calculation functions do not mutate CombatState or source stats.
- `CombatState.take_damage(D)` applies health loss, capped at remaining HP.
- Damage after resistance and actual health removed differ on overkill. D=100 against 20 remaining HP removes only 20 HP.
- Raw damage must be finite/nonnegative; resistance must be finite. Reject overflow rather than passing infinity to state.
- Use floats with no per-hit integer rounding. Display formatting such as `.4f` affects text only.
- Do not claim this rounding policy matches Riot's client; it is an explicit simplification. No hidden epsilon death threshold is applied at this stage.

## Implementation and tests

- `src/tft_simulator/combat/damage.py`: resistance multiplier, physical/magic/true calculations, model version marker.
- `tests/test_damage.py`: 23 cases for formula examples, zero/negative resistance, monotonicity, continuity, invalid inputs, overflow, and integration with HP state.
- Actual full local run: 64 passed. Default offline run: 48 passed, 16 skipped.
- No database source values or Notebook files were modified. The user confirmed the notebook damage examples match expected output. The 64-test figure above records the damage step; the timing step has since increased the total to 87.

## Still pending

Fixed attack timing and the deterministic ordinary-attack event loop are now implemented; see `attack-timing.md` and `basic-duel.md`. Simultaneous attacks use an explicitly chosen batch rule. Mana generation, skills, critical strikes, and special effects remain absent. User-run full-duel feedback is pending; Phase 4 acceptance is not complete.
