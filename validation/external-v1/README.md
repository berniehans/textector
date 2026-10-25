# external-v1 — benchmark consumido

590 casos: 90 fragmentos humanos de nueve ediciones digitales de 2018, 200 relatos
IA españoles de Gemini publicados y 300 generaciones literarias IberAuTexTification.
Evaluado una vez con f4-integridad sin ajustar parámetros. No es un holdout virgen.

Informe: ../../docs/validacion-externa-v1.md

`protocol.json` congela método, selección y exclusiones; `manifest.jsonl` identifica
los casos y hashes; `sources.json` fija fuentes/revisiones; `results.json` conserva
predicciones y abstenciones. `texts/` y `cache/` son locales y se ignoran en Git.

Restaurar: `python -B tools/fetch_external_corpus.py` desde la raíz del proyecto.
Reproducir: `python -B tools/validate_external.py --output reproduccion.json`.
Consultar LICENSES.md antes de reutilizar los textos de las fuentes.
