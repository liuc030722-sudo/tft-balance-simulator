# Phase 2: source selection and first acquisition step

Status: source audit completed on 2026-10-27. The user ran acquisition and normalization, reported a validated 15-row cohort with no missing fields, and completed simplified exports. Read-only inspection confirmed 15 records each in the saved champion and ability CSV files. Additional CSV readback/hash/export-manifest work was declined. The agent has not created or executed a Notebook or generated a processed dataset.

## Selected experiment version

- Set: 10, Remix Rumble
- Patch directory: `14.1`
- Language: `en_us`
- Source: https://raw.communitydragon.org/14.1/cdragon/tft/en_us.json
- Directory: https://raw.communitydragon.org/14.1/cdragon/tft/
- Official patch reference: https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-14-1-notes/
- Official set introduction: https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-13-23-notes/

Use the fixed patch directory rather than `latest` or `pbe`. The experiment version is the downloaded CommunityDragon archive snapshot identified by SHA-256, not a claim of exact regional deployment or a particular hotfix timestamp. Archive modification time is not the patch release date. Do not assign a release date from a directory listing or article publication time.

## Sources and confidence

| Data | Source / path | Interpretation and limitations |
|---|---|---|
| Official patch changes | Riot patch notes | Authoritative change descriptions; not a full numeric dataset |
| Champion identity | CDragon `sets["10"].champions[].apiName`, `name`, `cost`, `traits` | Traceable community extraction; validate playable-unit membership |
| Base HP, AD, AS | `stats.hp`, `stats.damage`, `stats.attackSpeed` | Preserve raw floats and nulls; confirm star-level semantics before deriving higher stars |
| Armor, MR, range | `stats.armor`, `stats.magicResist`, `stats.range` | Present in source; mechanics/units still require verification |
| Mana | `stats.initialMana`, `stats.mana` | Zero can be valid for passive units; do not treat it as missing automatically |
| Critical strikes | `stats.critChance`, `stats.critMultiplier` | Source values available; combat application is a later modeling task |
| Ability text and variables | `ability.name`, `ability.desc`, `ability.variables` | Text can contain templates; parameter arrays are not an executable ability implementation |
| Equipment and other entries | Root `items[].effects`, `desc`, `composition` | Mixed with augments and other-set records; cannot import wholesale as Set 10 equipment |
| Star-specific stats | Not a ready-made 1/2/3-star table here | Verify scaling separately; never invent values or array-index meaning |
| Full combat rules | Not specified completely by this JSON | Targeting, timing, mana lock, stacking, summons, etc. need separate verification |
| Player win rates | Not in this static source | No player API or player data is used in this step |

Riot Data Dragon documents TFT champion IDs/names/tier/images but does not promise the complete combat-stat schema needed here: https://developer.riotgames.com/docs/tft

CommunityDragon explicitly states that its TFT JSON is assembled from Riot files by the community, rather than directly authored by Riot: https://github.com/CommunityDragon/Docs/blob/master/assets.md#tft-and-arena-data

## Observed schema, not a permanent count contract

The source audit obtained HTTP 200 and 6,414,768 bytes. Root keys were `items`, `setData`, `sets`; set keys were `1`, `9`, `10`. `sets["10"]` contained 76 entity records, including special units such as Voidspawn with missing HP. Root `items` contained 1,156 records, including augments. These are audit observations, not a curated champion/equipment dataset. A normal project User-Agent was used; a request without that header received HTTP 403 during inspection.

The user acquisition should validate these structures again and report differences rather than hard-code the observed counts. Preserve the entire original byte stream and record UTC retrieval time, URL, SHA-256, byte length, and source headers. Do not save absolute local paths to shareable metadata. Use a new timestamped snapshot directory and exclusive file creation; never silently overwrite snapshots.

## Usage and attribution

Public access does not make Riot data public domain. Use the sources under applicable Riot policies, retain attribution, and include the required fan-project notice before publication. Review registration requirements before serving players. Code licensing must not purport to relicense Riot assets. Raw data remains ignored by Git for now; publish acquisition code and provenance rather than indiscriminately redistributing assets.

- https://www.communitydragon.org/
- https://www.riotgames.com/en/legal
- https://developer.riotgames.com/docs/tft

## Next step after acquisition feedback

Acquisition, normalization, and simplified export are complete for the reduced cohort. See `champion-data-dictionary.md` and `model-scope.md` for data definitions and deferred mechanics. Equipment is postponed. Raw star-level semantics and complete skill execution remain unverified. Do not create database schema or import data until the user confirms Phase 3.
