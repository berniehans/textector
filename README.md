# textector

CLI stdlib que puntúa un texto en español con un **índice heurístico
explicable de 0 a 100** (`indice_llm`): una suma ponderada de señales
(checks) asociadas a estilos de escritura frecuentes en texto generado por
LLM. Cada punto del índice se puede desglosar por check (valor bruto,
normalizado, peso, contribución, coverage), de ahí el "explicable".

> **Límite fundamental**: `indice_llm` es un índice heurístico; es un
> indicio, **no una probabilidad y no una prueba de autoría**. Nunca
> usarlo para acusar a una persona de haber usado o no IA.

## Uso

```bash
uv run python -B tools/cli.py analyze --archivo texto.txt --detallado
```

(`--stdin` en lugar de `--archivo` lee de la entrada estándar; solo se
admite una de las dos. `--json` emite el informe completo como JSON y
`--detallado` añade el desglose por check.)

Salida ilustrativa:

```
indice_llm=52 version=f2 n_disponibles=5
burstiness: valor_bruto={'n_oraciones': 7, ...} normalizado=0.3100 peso=0.1656 contribucion=3.2725 coverage=1.0000
...
cliches_es: valor_bruto={'n_tokens': 84, 'n_hits_total': 1, ...} normalizado=0.0000 peso=0.2370 contribucion=0.0000 coverage=1.0000
```

Los errores (archivo inexistente, YAML del config invalido, entrada vacia,
texto muy corto) se reportan en **una línea por stderr** con exit code 1:
sin traceback y sin volcar el contenido del archivo leído.

## Requisitos

- Python **3.11** (solo stdlib en runtime).
- `uv` solo para gestionar el entorno (`pyproject.toml` + `uv.lock` +
  `.python-version`); no es dependencia del programa.

## Cómo correr los tests

```bash
uv run python -B -m unittest discover -s tests -p "test_*.py" -v
```

Los tests de la CLI usan subprocess y archivos temporales creados en
`tempfile.mkdtemp()` (fuera del árbol del proyecto, con limpieza en
`tearDown`).

## Estado por fase

- `[x]` **F1 — lista**: esqueleto del proyecto + núcleo de texto
  (`tools/textector_core.py`), contrato de checks (`tools/checks/`), y el
  formato YAML-min del léxico documentado en `docs/audit_aifingerprint.md`
  y `docs/audit_zippy.md`.
- `[x]` **F2 — lista**: los 5 checks concretos (`burstiness`, `mattr`,
  `uniformity`, `cliches_es`, `compression`) con pesos y topes de grupo
  congelados en `tools/scoring.py`; la suite pasó de 76 a **79 tests verdes**.
- `[x]` **F3 — calibración contra corpus (resultado débil y honesto, dos rondas)**:
  v1 (20 textos): 5 casos de holdout, **3 falsos positivos** en prosa clásica.
  v2 (40 textos: 20 literatura PD + 10 narrativa IA + 10 noticias sintéticas
  CC-BY): holdout nuevo `{h08,h16,h19,a05,a07,b03}` → **0 falsos positivos**,
  pero **2 falsos negativos de narrativa IA + 1 abstención** y CV LOGO en TRAIN
  TPR 0.04 / TNR 0.24. Conclusión: **pre-filtro de dominio/estilo, no detector
  de autoría**; "humano" significa "sin señal suficiente", nunca exculpación.
  Detalle en `docs/calibration.md`.
- `[x]` **F4 — esta fase**: CLI `tools/cli.py analyze` con salida normal,
  `--json` y `--detallado` (desglose por check), reutilizando el pipeline
  congelado F2 (checks + `scoring.compute_indice`) y el parser YAML-min
  (`tools/lexicon`) para cargar el léxico completo de
  `config/cliches_es.yaml`.

## Límites

- **Sin red**: ninguna parte del código hace llamadas de red.
- **Sin escritura**: el CLI no escribe archivos; sus únicas entradas son el
  `--archivo`/`--stdin` y el config del léxico.
- **Corpus**: `corpus/` con las piezas y su procedencia documentadas en
  `corpus/manifest.csv`; la calibración F3 se hizo solo con ese corpus y el
  holdout no aporta semillas.

## Estructura

```
tools/textector_core.py   # normalize_text / tokenize / split_sentences (puras, sin I/O)
tools/checks/             # CheckResult + protocolo Check + los 5 checks F2
tools/scoring.py          # pesos, topes de grupo, compute_indice (congelado en F2)
tools/lexicon.py          # parser YAML-min fail-closed
tools/cli.py              # CLI F4: subcomando analyze
tools/calibrate.py        # split por grupos + barrido + holdout (F3)
config/cliches_es.yaml    # léxico YAML-min completo (fuente de la verdad)
corpus/                   # corpus + manifest.csv (procedencia)
docs/                     # auditorías de los referenciales + methodology.md
```

Solo stdlib de Python 3.11. Gestión con uv (`pyproject.toml` + `uv.lock` +
`.python-version`), pero uv no es dependencia en runtime.
