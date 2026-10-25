# Evidence F1 — textector (24-oct-2026)

- Run coder one-shot: grant `grant-4ae3399ea164` (12 paths, TTL ≤ 900 s) + fix slice (3 paths, grant emitido).
- Suite: `uv run python -B -m unittest discover -s tests -p "test_*.py" -v` → **OK (skipped=8)**, REAL_EXIT=0. 30 tests (22 ok, 8 skipUnless se activan con `tools/lexicon.py` en F2).
- Smoke manual: `S01 —` filtrado; diálogo «—» por línea abre réplica; `Sr.`/`p. ej.` no cortan; spans invariantes (`text[start:end]==span.text`).
- Hashes: core `0aedcd33…`, test_segmentacion `ca46a56a…`, audit_aifingerprint `754d2527…`.
- Mojibake: 0 (CJK scan limpio en los 5 archivos de texto).
- Incidentes documentados: 4 write_file bloqueados por guard → resueltos con patch;spent: caracteres ramdom corregidos vía patch.
- OTRO motor: parche del core Hermes (`agent/session_client_env.py` + plugin `coder-auto-route` 1.0.1) — modificaciones en el repo hermes-agent (sin commit): snapshot en `cache/scratch/testector/bootstrap-snap/`.
