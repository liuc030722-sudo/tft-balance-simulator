-- Execute manually ONLY after confirming the target database is absent.
-- Connect to the postgres maintenance database, with auto-commit enabled.
-- PostgreSQL CREATE DATABASE cannot run inside a transaction block.
CREATE DATABASE tft_balance_simulator;
