# Guía de uso — textector

CLI local (Python 3.11 + stdlib) que calcula un **índice heurístico explicable 0–100** de señales de prosa típica de LLM en español, con un diagnóstico de dos ejes (prosa vs estructura). **No es una probabilidad ni una prueba de autoría**: es un pre-filtro; fuera de la banda el resultado es un indicio a revisar.

## Requisitos

- Python 3.11 (el proyecto fija `.python-version` = 3.11).
- `uv` para el entorno (runtime **sin dependencias**).
- **Semillas de compresión**: `corpus/seeds/seed_ia_es.txt` y
  `corpus/seeds/seed_hum_es.txt`. El análisis las usa siempre (señal
  `f3-semillas`) y es **fail-closed**: si faltan o no son legibles, el CLI
  aborta con exit 1 y **no emite índice**.

```bash
cd workspace/textector
uv sync                      # crea/actualiza .venv desde uv.lock
```

## Uso básico

```bash
uv run python tools/cli.py analyze --archivo ruta/al/texto.txt
uv run python tools/cli.py analyze --stdin < texto.txt
```

Salida por defecto (una línea):

```
indice_llm=24 version=f2 n_disponibles=5
```

## Flags

| Flag | Qué hace |
|---|---|
| `--archivo RUTA` / `--stdin` | Entrada (mutuamente excluyentes, obligatorio uno) |
| `--json` | Informe completo en JSON ordenado (contribuciones, pesos, coverage) |
| `--detallado` | Desglose por check: valor bruto, normalizado, peso, contribución, coverage |
| `--diagnostico` | Bloque de dos ejes (prosa vs estructura) con categoría y nota |
| `--config RUTA` | Léxico YAML-min alternativo (por defecto `config/cliches_es.yaml`) |

## Ejemplo real

```bash
uv run python tools/cli.py analyze --archivo mi_texto.txt --diagnostico
# indice_llm=24 version=f2 n_disponibles=5
# diagnostico: categoria=prosa_no_concluyente prosa=24 estructura=67 no_concluyente=True
# nota: El índice de prosa (24) cae en la banda de abstención [18, 26): decisión no
#       concluyente. Estructura: regular (valor 67). Ojo: 'estructura regular' no
#       distingue una plantilla generada de un formato de trabajo propio.
```

## Cómo leer el resultado

1. **Umbral congelado**: 26, margen 8 → **banda de abstención `[18, 26)`**.
2. `indice_llm >= 26` → señal de prosa marcada (no veredicto).
3. `18 <= indice < 26` → **no concluyente** (banda).
4. `indice <= 18` → sin señal de prosa por estos checks (tampoco exculpa).
5. `--diagnostico` añade la lectura estructural: solo la categoría
   `plantilla_prosa_y_estructura` es concluyente; el resto son
   `no_concluyente=True`.

## Errores y códigos

| Situación | Comportamiento |
|---|---|
| Archivo inexistente / no UTF-8 | `error: …` en stderr, **exit 1**, sin volcar contenido |
| YAML inválido o con claves no permitidas | `error: config YAML invalido (línea N): …`, exit 1 |
| Entrada vacía | `error: entrada vacia…`, exit 1 |
| Texto demasiado corto (cobertura < 5 checks) | `error: texto muy corto…`, exit 1, **sin número** |
| Semillas de compresión ausentes o ilegibles | `error: …` de una línea, **exit 1**, sin emitir índice (fail-closed) |

### Campos de versión en la salida

Toda salida (`--json` y humana) declara el método y la señal:

- `"version": "f3-semillas"` — versión del método (los índices **no** son
  comparables con los de `f2`).
- `"semillas": "reales-es"` — la compresión sembada usó las semillas ES reales
  del corpus (no las fixtures sintéticas de F2).

## Tests

```bash
uv run python -B -m unittest discover -s tests -p "test_*.py" -v
```

## Documentos relacionados

- `docs/arquitectura.md` — módulos y flujo.
- `docs/checks.md` — qué mide cada check y sus pesos.
- `docs/calibration.md` — matriz real de calibración (v1 y v2) y límites.
- `docs/diagnostico-hibrido.md` — los dos ejes y la tabla de categorías.
- `docs/corpus.md` — corpus, procedencia/licencias y semillas.
- `docs/analisis-manual-llm.md` — análisis forense manual asistido por LLM.
- `docs/methodology.md` — decisiones de método congeladas (F2).
- `NOTICE` — atribuciones MIT de los ports.
