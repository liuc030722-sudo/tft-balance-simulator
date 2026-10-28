# Phase 3: reusable read-only queries

## Implemented

`src/tft_simulator/database/queries.py` provides:

| Function | Return value |
|---|---|
| read_connection() | Context manager yielding a connection with read-only transactions |
| list_versions(connection) | List of source-version dictionaries |
| list_champions(connection, version_id, cost=None) | List of hero dictionaries, optionally filtered by cost |
| get_champion(connection, version_id, champion_id) | Full raw-stat dictionary, or None if absent |
| get_ability(connection, version_id, champion_id) | Skill dictionary with decoded JSONB, or None |
| get_counts(connection, version_id) | Counts for the specified version |

All data queries require a connection. Hero queries explicitly specify a version ID; the current imported source snapshot has version_id=1. This is an internal row identifier, distinct from Set number 10 and Patch text 14.1. No automatic latest-version selection occurs. Lists return empty lists for absent versions; single-record lookups return None.

`query.py` is the command-line entry point. Business queries stay in `queries.py` so a future battle engine or application can reuse them without parsing command-line output.

## PowerShell

From the desktop project root:

```powershell
.\.venv\Scripts\python.exe -m tft_simulator.database.query versions
.\.venv\Scripts\python.exe -m tft_simulator.database.query counts --version-id 1
.\.venv\Scripts\python.exe -m tft_simulator.database.query list --version-id 1 --cost 2
.\.venv\Scripts\python.exe -m tft_simulator.database.query show --version-id 1 --champion-id TFT10_Annie
```

Expected: version 1 identifies Set 10 / patch 14.1; counts are 1/15/15; the cost filter returns Garen, Jax, Senna. Annie shows HP 450 and the ability Disintegrate. An unknown hero ID prints a not-found message and exits with code 1. Output is JSON; dates are formatted as strings for display.

## Key Python and SQL concepts

- `with read_connection() as connection`: opens the configured database, verifies its name, enables read-only transactions, and closes the connection on exit. Read-only mode is for query connections only; the importer retains its separate write connection.
- `@contextmanager` and `yield`: make the function usable with `with`; execution pauses at yield while the caller uses the connection, then resumes cleanup on exit.
- A cursor sends SQL and fetches results. `dict_row` gives named columns rather than positional tuples.
- `fetchall()` returns a list; `fetchone()` returns one row or None.
- `%s` placeholders bind values separately from query text. Do not interpolate user-supplied IDs using f-strings.
- The list query appends only a fixed cost-filter fragment; cost and version values remain separate parameters.
- LEFT JOIN retains a hero even if its ability container is absent. Both version_id and champion_id belong in the join condition.
- PostgreSQL TEXT[] becomes a Python list; JSONB becomes Python lists/dictionaries automatically. Do not call json.loads again on an already decoded list.
- Type annotations document inputs and outputs; they do not replace runtime validation or imply a star-level interpretation.

## Notebook usage

The user may manually add query cells to the current Notebook or create a new one. Select the existing project `.venv`. Import the installed editable package and call its functions; PROJECT_ROOT and raw-file download are not needed for these queries because config.py locates the local .env relative to its source file. All Notebook code is supplied in chat; no Notebook was created, edited, or executed by the agent.

## Verification

On 2026-10-28, all 20 tests passed in a combined run, including 7 real read-only PostgreSQL integration cases. Actual command-line versions/counts/cost-filter/detail lookups succeeded; unknown-ID exit behavior was checked too.

During the combined run, an earlier configuration test was found to leak a synthetic dotenv password into the test process environment. `tests/test_config.py` now isolates and restores the entire environment mapping, including keys dotenv itself creates. The production .env and database password were not changed.

The query-step record above reflects 20 tests at that stage. Phase 3 now also includes transaction-isolated maintenance tests; the full suite has 29 tests. Default offline run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: 13 passed, 16 skipped. Opt in to local integration tests only after importing the documented source snapshot:

```powershell
$env:TFT_TEST_DATABASE = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TFT_TEST_DATABASE
```

Expected: 29 passed. Query tests remain read-only; maintenance tests create and modify only uncommitted TEST_ONLY fixtures with forced rollback. See `database-crud.md`.

## Boundaries

The query step did not modify hero attributes, schema, or row counts. Maintenance CRUD has since been implemented and tested without changing source records; see `database-crud.md`. The reduced Phase 3 has passed; see `phase3-validation.md`. Combat models, star scaling, equipment, and simulation are not implemented.

Suggested commit: `feat: add version-aware database queries and integration tests`
