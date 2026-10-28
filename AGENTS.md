# Project collaboration rules

- Continue the existing Phase 1–10 plan. Start the next phase only after explicit user confirmation.
- Never create, edit, overwrite, delete, or execute any `.ipynb` file, including through scripts or notebook tools.
- Supply all notebook exploration, ingestion, cleaning, analysis, and visualization code in chat as sequential code blocks. The user copies and runs it, then reports results. Do not assume it succeeded.
- Each Python block or meaningful code section must contain useful Chinese `#` comments. Explain purpose, inputs, outputs, important syntax, and expected results after each chat block.
- Provide one coherent development step at a time; do not output an entire phase before feedback.
- Production application logic belongs in modular `.py` files, not notebooks. Non-notebook files may be edited directly; explain edits to the user.
- Provide database SQL for the user to execute in DBeaver. Never recreate, clear, or overwrite existing data without explicit authorization.
- Keep all project files in this desktop project. Detect the configured Windows desktop with registry configuration and pathlib; never assume a drive.
- Use the existing Python 3.13.16 `.venv`. Keep secrets in environment variables/local `.env`; never print or commit credentials or user-specific absolute paths.
- Use verifiable Riot or CommunityDragon data with Set, Patch, retrieval time, source URL, and raw-byte hash. Preserve missing values and document derived or unsupported fields.
- Distinguish source facts, verified mechanics, simplified assumptions, simulation results, and player match data.
- Prefer the minimum necessary code and explanations. The user declined layered CSV readback/hash/export-manifest checks; do not reintroduce them as requirements.
- Follow `docs/model-scope.md`: equipment, trait and Headliner bonuses, and star-scaling calculations are deferred. Target a fixed one-star baseline, but do not label source stats as verified one-star stats before checking that meaning. Do not infer star levels from parameter-array length.
- The user explicitly authorized first GitHub publication and inclusion of the four existing saved notebooks. A read-only privacy check passed; .gitignore names those four files explicitly. Other notebooks remain ignored. Never edit or execute notebooks, and never force-add unreviewed files. Future commits/pushes require an upload request; guidance alone is not authorization.
