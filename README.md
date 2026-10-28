# Auto Battler Combat Balance Simulator

A Python-based TFT combat simulation and balance analysis framework using PostgreSQL, Monte Carlo methods, and interactive data visualization.

## Project status

Implemented: versioned source data, PostgreSQL schema/import/queries, explicit champion-maintenance CRUD, automated tests, immutable attributes and per-battle state, provisional damage/timing models, and a deterministic ordinary-attack 1v1 event simulator with structured logs. Skills/passives, Monte Carlo batches, balance analytics, and Streamlit are **not implemented yet**.

Phase 1 acceptance passed on 2026-10-27: Python 3.13.16 virtual environment, dependency checks, 6 offline tests, and an authenticated connection to `tft_balance_simulator` on PostgreSQL 18.6. See `docs/phase1-validation.md`.

Phase 2 uses the CommunityDragon Set 10 / patch 14.1 archive. The user acquired the raw snapshot, validated a 15-champion DataFrame, and saved champion and raw-ability CSV files with 15 records each. See `docs/champion-data-dictionary.md`. The reduced first version defers equipment, trait/Headliner bonuses, and star scaling; see `docs/model-scope.md`. Complete ability mechanics and source star-level semantics remain unverified. Notebook code is provided in chat only; the agent never creates, edits, deletes, or executes `.ipynb` files. Optional dependency groups supply `ipykernel` (`notebook`) and pandas (`analysis`).

The reduced Phase 3 has passed. The database contains 1 version, 15 champions, and 15 ability records. Repeating the import added no duplicates. All 29 tests pass with local database tests enabled (default: 13 passed, 16 skipped). Maintenance tests roll back only newly created TEST_ONLY fixtures; source records remain unchanged. See `docs/phase3-validation.md` for acceptance, `docs/database-schema.md` for design, and `docs/database-crud.md` for access-layer details. Do not rerun `sql/schema.sql` on the existing schema.

The simplified Phase 4 ordinary-attack baseline has passed user-run acceptance: full-duel summary, 23 event records, and the 5-second timeout example match expected outputs. All 106 local tests passed (default: 90 passed, 16 skipped). Resistance and timing assumptions remain unverified against full Patch 14.1 client behavior. See `docs/phase4-validation.md` and `docs/basic-duel.md`. This is not a complete TFT combat engine.

## Research goals

Study standardized champion matchups, attribute sensitivity, equipment interactions, and balance experiments under explicitly documented assumptions. Simulated win rates will describe this model and its test scenarios; they are not ranked TFT win rates or official Riot Games balance conclusions.

## Environment

- Windows and PowerShell
- Existing Python **3.13.16** installation; project-local `.venv`
- PostgreSQL 18 (user-specified target: 18.6), localhost port 5432
- Database: `tft_balance_simulator`
- Git, VS Code, and DBeaver

## Installation

Open this project folder in VS Code, then open its PowerShell terminal. The initial setup already creates `.venv`; recreate it only when needed using your installed Python 3.13.16:

```powershell
py -3.13 -c "import sys; print(sys.version)"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

The lock snapshot records the packages validated during Phase 1 on Windows/Python 3.13.16. `pyproject.toml` expresses supported dependency ranges. For a fresh dependency resolution instead of the snapshot:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

In VS Code, run **Python: Select Interpreter** and choose `.venv\Scripts\python.exe`. The Python extension is needed for interpreter selection/debugging. Direct interpreter commands below do not require PowerShell activation or execution-policy changes.

## Local configuration

`.env` is local and ignored by Git. If absent, copy `.env.example` once:

```powershell
if (!(Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
code .env
```

Fill in `DB_PASSWORD` locally. Do not paste credentials into chat or commit them. Use single quotes around values containing `#` or spaces. Existing process environment variables override `.env`. The configuration uses separate connection parameters so passwords do not require URL encoding. No API key is needed for Phase 1.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tft_simulator.environment
git status --short
git check-ignore .env .venv
```

The environment command returns exit code 0 only when Python is 3.13.16 and the target database accepts a connection. Offline tests do not establish database connectivity. Connection failures print only exception type and SQLSTATE, to avoid disclosing credentials. Consult DBeaver locally for detailed authentication errors.

## DBeaver checks

Create/open a PostgreSQL connection to `localhost:5432`, user `postgres`, initially database `postgres`. Enter the password in DBeaver locally and click **Test Connection**. Open an SQL editor and run:

```sql
SELECT current_database(), current_setting('server_version');
SELECT datname FROM pg_database WHERE datname = 'tft_balance_simulator';
```

Only if the second query returns no rows, open `sql/create_database.sql` and execute its statement with auto-commit enabled against `postgres`. This step creates an empty database; it does not create tables. Refresh the navigator and configure the project connection to use `tft_balance_simulator`. Re-run the Python environment check. Do not execute the creation script if the database already exists. No database is automatically created, cleared, or overwritten.

## Layout

```text
src/tft_simulator/  Configuration and environment validation
tests/             Offline configuration tests
sql/               Optional database creation script; queries/ reserved
scripts/           Desktop location utility
docs/              Phase notes and local validation instructions
data/              raw/, processed/, sources/ reserved for Phase 2
app/               Reserved for a later Streamlit application
notebooks/         Reserved for analysis
reports/figures/   Reserved for generated figures
```

Empty directories use `.gitkeep`. Later-phase modules and table definitions will be added only in their respective phases. Raw/processed datasets and generated figures are ignored by default pending a documented data-sharing policy.

## Reproducibility and security

Do not commit `.env`, `.venv`, credentials, local absolute paths, or machine-specific settings. Before staging changes, inspect `git diff` and `git status`. GitHub publication and commits are not performed automatically during initialization. Source records, data licensing/usage requirements, model assumptions, seeds, and experiment metadata will be documented as those features are implemented.

The four existing notebooks are included with author approval after a read-only privacy review. Additional notebooks and local datasets remain excluded. A fresh clone can install the code and run offline tests; source-backed database runs require manual data preparation and local PostgreSQL setup. A one-command end-to-end reproduction workflow is not implemented. See `docs/github-guide.md` for upload, updates, privacy, and backup guidance.

For notebook work with a fresh dependency resolution, install `python -m pip install -e ".[dev,notebook,analysis]"` inside the virtual environment. Select that environment's kernel in VS Code, run notebooks in numbered order, and adjust snapshot filenames to your own acquisition output where needed.

This is an unofficial personal research project. TFT game data remains Riot Games' intellectual property. This project is not endorsed or sponsored by Riot Games. A future code license does not relicense third-party data or assets.

## Next phase

The simplified Phase 4 runtime acceptance has passed; Phase 5 awaits explicit user authorization. Equipment remains deferred. Interpretation limits are documented in `docs/model-scope.md`, `docs/combat-mechanics.md`, `docs/attack-timing.md`, and `docs/basic-duel.md`. Real hero passives and skill effects remain disabled.
