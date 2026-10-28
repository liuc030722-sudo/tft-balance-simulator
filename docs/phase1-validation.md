# Phase 1 validation record

Validated on 2026-10-27, Windows:

| Check | Result |
|---|---|
| Desktop discovery | Registry configuration resolved using pathlib; directory exists |
| Existing project safety | Target absent before creation; no existing project overwritten |
| Python / virtual environment | Python 3.13.16; project `.venv` created |
| Dependencies | Installed editable project with dev dependencies; `pip check` passed |
| Tests | 6 passed |
| Git | Initialized with branch `main`; no commit or remote created |
| Secret isolation | `.env`, `.venv`, and `.vscode` ignored |
| VS Code | Folder-open command succeeded; Python extension present |
| PostgreSQL service | Windows service running; localhost:5432 accepts connections |
| PostgreSQL client | psql 18.6 |
| PostgreSQL server | Authenticated query confirmed 18.6 |
| PostgreSQL authentication | Maintenance database `postgres` connected successfully after local credential configuration |
| Target database | Connected successfully to `tft_balance_simulator` using project configuration after user created it in DBeaver |

After the user created the database in DBeaver, the remaining checks were repeated. The project environment command successfully connected to `tft_balance_simulator` and confirmed PostgreSQL 18.6. A separate read-only transaction verified the database name, server version, and a constant query result. The virtual environment uses Python 3.13.16, `pip check` passes, all 6 offline tests pass, and all reserved project directories exist.

Phase 1 acceptance: **PASS**. No game data, schema tables, combat engine, or simulation results were created. The agent did not create, delete, or modify database data during validation. Phase 2 has not begun and requires user confirmation.
