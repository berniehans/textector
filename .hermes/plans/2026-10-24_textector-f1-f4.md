# PLAN — textector v2 (24-oct-2026)

**Proyecto:** detector local de texto IA en español · Python stdlib · CLI · sin dependencias runtime.
**Estado:** F1 lista para ejecutar, **bloqueada por regresión del runtime de Hermes** (fix pendiente de decisión: parche de core vs esperar upstream). Nada codificado aún.
**Fuente de verdad:** este documento + `docs/methodology.md` (nace en F2). Ejecución: solo bot `coder` vía one-shot con scope inyectado (rutas exactas, TTL ≤ 900 s, `write_file`; nunca `patch` con Delete+Add del mismo path). El maestro planifica, verifica (solo lectura) y corre los tests con `uv run`.

## Objeto y límites honestos

- Score: **`indice_llm`** — índice heurístico explicable 0–100 de *señales asociadas a generación LLM en español*. **NO** es una probabilidad de generación ni una prueba de autoría; es un indicio, jamás un veredicto (decisión recomendada por @planner y adoptada por defecto; si algún día exige "probabilidad calibrada", es un gate estadístico aparte con corpus mucho mayor).
- Abstención: sin cobertura suficiente el resultado es `insufficient_text` (sin número, exit ≠ 0).
- Privacidad: nunca imprime texto crudo por defecto; posiciones/conteos anonimizados; sin red ni escritura en uso normal.
- Registro literario: un texto literario por sí solo nunca demuestra origen (los LLM producen ficción sobria muy pulida — la perfección estructural es sospecha, no prueba).

## Evidencia de investigación (verificada en fuentes primarias, 24-oct)

| Fuente | Licencia | Aporta | Decisión |
|---|---|---|---|
| `thinkst/zippy` (0.1.3, 296★) | MIT | Compresión sembrada (zlib/LZMA, delta vs semilla IA + normalización por longitud; su README y Discussion #5) y `burstiness.py` | Port del *mecanismo* con atribución |
| `AIStoryHub_LLM_Cliche_Corpus` (v1.7, 758 entradas EN) | MIT | Léxico de clichés IA con fuentes académicas y peso 0–100 por entrada, categoría *fiction clichés* | Semilla → derivar ES + señales propias |
| aifingerprint (PyPI 1.6.0, 0★, MIT en repo) | MIT | Score 0–100 explicable con 10 checks ponderados (`analyzer.py`, `checks/`) | Auditoría punto por punto → port |
| MINT/DetectGPT/Binoculars/GLTR; GPTZero/isgen | — | SOTA académico / SaaS | Descartados: requieren torch/HF o son cerrados |

- **Piloto empírico** (entorno desechable, uv): aifingerprint → objetivo ES 14/100; IA-ES 32; IA-EN 32; humano-EN 16. zippy → 0.669/0.344/0.161/0.157 (margen EN≈0.004 = ruido; su README admite poor results no-INGLÉS). Conclusión: nada plug-and-play en español → híbrido (port MIT, no dependencia).
- Localización del gap: la adaptación al español (léxico ES + semillas ES + calibración ES) es el diferenciador; nadie lo ha publicado.

## Environment / invariantes de proyecto

- Windows 11, git-bash; `python` ≠ stub (`python3` = stub de Store); intérprete fijado por `.python-version` = 3.11 (venv creado: `textector/.venv` 3.11.15).
- **UV para todo** (venvs, installs, lock): `uv venv`/`uv sync`/`uv lock`; el lockfile se GENERA con UV, nunca a mano. Los comandos UV mutantes los ejecuta el maestro con permiso ya dado ("usa uv para todo").
- Estándares de repo: `tools/`, `docs/`, `tests/`, `config/`, `.gitignore`, `os.path.dirname(...)` para paths, resultados reproducibles y deterministas.
- Tests: stdlib `unittest` (no pytest en repo); `python -B`; fixtures ES deterministas; tests no escriben en el repo (temporales bajo TMPDIR de Hermes).
- Git: sin init/commit/push hasta cierre F4 con orden explícita.

## Fases (gates de test)

### F1 — Entorno UV + núcleo de texto (prioridad inmediata)
- **Entregables (12 rutas exactas):** `pyproject.toml` (requires-python ≥3.11, sin deps) · `.python-version` · `.gitignore` · `README.md` (aviso heurístico) · `tools/textector_core.py` (normalize NFC/casefold, tokenize Unicode, split_sentences ES conservador con spans: abreviaturas `Sr./Dra./p. ej.`, `¿?`/`¡!`, elipsis, rayas de diálogo «—» no fuerzan oración nueva, encabezados `S01 —` no son prosa) · `tools/checks/__init__.py` + `registry.py` (CheckResult/Check con firma común y `insufficient`) · `config/cliches_es.yaml` (esqueleto YAML-min) · `tests/test_segmentacion.py` · `tests/test_yaml_lexicon.py` (fail-closed ante tags/alias/anidados/multilínea/comentario inline/duplicados) · `docs/audit_aifingerprint.md` · `docs/audit_zippy.md` (auditoría con citas archivo/función).
- **Gate:** RED→GREEN; `uv run python -B -m unittest discover -s tests -p "test_*.py" -v` exit 0 (colección >0, sin número mágico); `uv run python --version` = 3.11.x; revisión manual de spans; contraste del port vs fuente MIT.
- **NO:** corpus, puntuar el texto externo, instalar las 2 herramientas como dependencias, git init.
- **Backtrack:** revertir solo archivos nuevos del slice (proyecto entero es nuevo).

### F2 — Port de checks + features ES + scoring explicable
- **Bloques:** (1) `burstiness` robusta (mediana/MAD, n reportado, efecto diálogo); (2) `compression` **método zippy redefinido**: deltas vs semilla IA y semilla humana, normalizados por bytes del texto (raw DEFLATE `zlib.compressobj(level=6, wbits=-15)`); mecanismo probado en F2 con **semillas sintéticas deterministas de fixture** (las reales ES llegan en F3); (3) `cliches_es.py` con el YAML-min (de AIStoryHub traducido/adaptado + español narrativo nativo: perifrases «una X que parecía…», «de quien», listas 3-en-3, cierre «en conclusión», muletillas; pesos y fuentes citadas); (4) `uniformity` (dispersión de párrafos + repetición de conectores/aperturas, indicadores separados); (5) `mattr` ventana fija documentada (50 tokens), sin sustituir TTR silenciosamente. Port auditado de pesos de aifingerprint con mapping documentado check→regla ES→peso; descartes motivados; NOTICE MIT (aifingerprint + corpus).
- **Scoring:** contribución `100·wᵢ·qᵢ/Σw_disponibles`; score entero 0..100 = suma de contribuciones (coherencia exacta salvo redondeo declarado); correlaciones TTR/burstiness y cliché/uniformidad diagnóstico + tope de peso conjunto; **transformaciones y pesos congelados ANTES de F3**; mínimos de cobertura → `insufficient_text`.
- **Gate:** suites exit 0; casos que aíslan cada contribución; invarianza aproximada a duplicar texto; JSON determinista; `NO` llamar «calibrado».
- **Backtrack:** revertir solo los archivos de este slice.

### F3 — Corpus 10+10 + semillas ES + calibración honesta
- **Corpus:** `corpus/human/h01..h10.txt` + `corpus/llm/a01..a10.txt` ES genuinos, emparejados por género/longitud/tema, con procedencia/licencia/permiso, autor o modelo/prompt pseudonimizados, checksum, redistribución restringida; **narrativo humano creativo incluido** para medir FP.
- **Semillas ES de compresión SOLO desde el subconjunto IA de train** (jamás holdout, jamás EN); `corpus/seeds/`.
- **Método:** split por grupos (autor/prompt), pesos ya congelados; umbral elegido solo con train (CV por grupos); **holdout abre UNA vez**: TP/FP/TN/FN, FP literario ES, sensibilidad, abstenciones, variación por fold.
- **Gate:** 10+10 válidos con licencias; tests de split/contaminación/reproducibilidad/manifest inválido; informe etiquetado `experimental` con fallos incluidos; si FP literario alto → abstención o retirar check (nunca "detector confiable").
- **Backtrack:** revertir parámetros/umbral; conservar corpus y evidencia anonimizada; no retocar holdout para fabricar mejora.

### F4 — CLI + empaque + verificación final
- **CLI:** `python -B tools/textector.py analyze --input <ruta>|--stdin --format json --explain --lexicon config/cliches_es.yaml`; errores exit≠0 sin traceback con texto privado; salida sin fragmentos crudos salvo opción explícita; cobertura/abstención visible; versión de método/lexicon reportada.
- **uv.lock:** SOLO generado con `uv lock`/`uv sync` bajo permiso (ya concedido para UV).
- **Gate final maestro:** suite completa exit 0 con `uv run`; `uv run python --version` 3.11.x; inventario de archivos/hashes; sin secretos ni outputs crudos; smoke opcional del texto externo (un caso, sin etiqueta, sin conclusión de origen). Commit/push solo con orden explícita.

## Supuestos
1. El piloto (14/32/32/16) lo reportó el maestro; planner no lo verificó — el coder auditará las fuentes punto por punto antes de portar, y el maestro contrastará.
2. La política de sanitizer del runtime manda: si upstream no repara la inyección, F1 queda bloqueado (no degradar silenciosamente, no saltar mutadores).
3. Corpus 10+10 construible con permisos/licencias de sus autores (10 humanos + 10 IA-ES con registro de modelo/prompt).
4. El texto de `composer-pastes` es legible para smoke con permiso tácito; queda FUERA de entrenamiento y calibración y sin etiqueta.

## Criterios de aceptación (verticales)
1. Cada fase cierra con suite REG→GREEN exit 0 + evidencia en disco (fixtures, matrices, informes) verificada por el maestro.
2. Score reproducible/determinista; suma de contribuciones == score salvo redondeo declarado; `limitations` y cobertura siempre visibles.
3. Nunca dice «probabilidad», «calibrado» (sin F3 experimental) ni «prueba de autoría».
4. Nada fuera del workspace; sin red/escrituras en uso normal; sin commit/push sin orden.
5. El port MIT se contrasta contra la fuente y se descarta/ex Tradición con motivo documentado.

## Riesgos top-3
1. **Sobreinterpretación del índice como prueba/probabilidad** (falsos positivos dañinos, textos formales/académicos) → etiqueta `indice_llm`, abstención, nunca decisión automática; el README y el `--explain` lo repiten.
2. **Autocontaminación con 20 textos** (semillas del mismo corpus evaluado; fuga autor/prompt/género/longitud) → semillas solo de train IA, holdout jamás en semillas, CV por grupos, pesos congelados, FP literario reportado.
3. **Port defectuoso/sesgo EN residual + Composer/parser bias** (cliché traducido puede no señalar en ES) → auditoría punto por punto, descartes motivados, señales ES nativas, fixtures de español literario, revisión del maestro vs fuente MIT.

## Bloqueo actual y rollback global
- **F1 en espera del gate de confianza del runtime** (regresión documentada por el core a session_client_env.py). Decisión de Bernie: parche del core (con snapshot + test + restart) o esperar upstream.
- Rollback: restaurar snapshot de la fase anterior; el texto externo nunca se modifica; Testment y otros workspaces intocables.

## Pendientes del usuario (recap)
1. Ratificar `indice_llm` heurístico (recomendado; adoptado por defecto).
2. Autorización de construcción/adquisición de corpus 10+10 ES con política de licencias y retención (F3).
3. Parche del core vs upstream (bloqueo F1).
