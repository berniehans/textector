# Arquitectura — textector

## Principios

- **Solo stdlib en runtime**: el proyecto corre con Python 3.11 sin dependencias; `uv` gestiona el entorno, no forma parte del producto.
- **Score congelado**: las transformaciones, pesos y umbral de la fase F2 están fijados por escrito (`docs/methodology.md`) y no se recalibran al añadir ejes nuevos.
- **Determinismo**: sin red, sin aleatoriedad no sembrada, salida JSON ordenada (`sort_keys`).
- **Honestidad por diseño**: abstención explícita, `no_concluyente` por defecto, y ningún texto crudo en la salida salvo petición.

## Módulos

```
tools/
  cli.py               CLI: analyze (--archivo/--stdin, --json, --detallado, --diagnostico)
  textector_core.py    normalize_text · tokenize · split_sentences (spans al original)
  lexicon.py           parser YAML-min fail-closed del léxico de clichés
  checks/
    __init__.py        CheckResult / Check (contrato común)
    registry.py        registro de checks
    burstiness.py      dispersión robusta de longitudes de oración
    mattr.py           diversidad léxica en ventana fija (50 tokens)
    uniformity.py      dispersión de párrafos + repetición de conectores/aperturas
    cliches_es.py      hits del léxico ES (densidad por 1000 tokens)
    compression.py     compresión sembrada (raw DEFLATE) vs semillas IA/humana
  scoring.py           contribucion = 100·w·q/Σw_disponibles → indice_llm 0..100
  estructura.py        eje estructural: secciones Sxx, largos, párrafos, diálogo
  diagnostico.py       tabla de categorías prosa × estructura + no_concluyente
  calibrate.py         split por grupos, LOGO-CV en train, holdout único
config/cliches_es.yaml léxico editable (YAML-min)
corpus/                human/ llm/ news/ seeds/ manifest.csv
docs/                  guía, arquitectura, checks, método, calibración, corpus
tests/                 unittest (sin red, temporales fuera del repo)
```

## Flujo de `analyze`

```
entrada (archivo/stdin)
   │  normalize_text (NFC + casefold)
   ▼
split_sentences (spans) ──► tokenize
   │
   ├─ burstiness ─┐
   ├─ mattr       │
   ├─ uniformity  ├─► CheckResult(valor_bruto, normalizado, peso, contribucion, coverage)
   ├─ cliches_es  │        │
   └─ compression ┘        ▼
                    scoring.compute_indice → indice_llm, contribuciones, coverage
                           │
   (opcional --diagnostico) estructura.eje_estructura(texto)
                           ▼
                    diagnostico.diagnostico_hibrido(informe, eje) → categoria, nota
```

## Contrato de checks

Cada check devuelve `CheckResult` con:

- `valor_bruto`: métrica nativa (dict de apoyo explicativo).
- `normalizado` ∈ [0,1]: transformación monótona documentada.
- `peso`: fijo (congelado en F2; topes de grupo para checks correlacionados).
- `contribucion`: `100·w·q / Σ w_disponibles`.
- `coverage` y `insufficient`: si no hay material suficiente, el check queda fuera y el score renormaliza; con los 5 fuera, `insufficient_text` y exit ≠ 0.

## Decisiones de diseño relevantes

| Decisión | Motivo |
|---|---|
| YAML-min propio (no PyYAML) | Restricción stdlib; gramática deliberadamente mínima y fail-closed |
| Segmentación ES conservadora | Rayas de diálogo, abreviaturas, `S01 —` como cabecera no-prosa |
| Compresión sembrada (port de zippy, MIT) | Aproxima predecibilidad sin modelos; semillas ES del train |
| Estructura separada del score | El caso «estructura humana + prosa IA» no debe contaminar el índice |
| Diagnóstico por categorías | Evita binario falso: solo una categoría es concluyente |

## Ejecución y empaquetado

- Entorno: `uv sync` (lockfile real, sin deps runtime).
- Tests: `uv run python -B -m unittest discover -s tests -p "test_*.py"`.
- Sin commit/push automáticos; sin red en ejecución normal.
