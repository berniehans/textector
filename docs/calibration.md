# Calibración F3 de textector — `tools/calibrate.py`

> **Estado: EXPERIMENTAL.** Todo lo que sale de esta calibración es un
> **índice heurístico, NO probatorio**: no es probabilidad, no es prueba de
> autoría ni evidencia legal. Ver `pyproject.toml` (descripción del
> proyecto) y `docs/methodology.md`.

## Estado de ejecución

**Archivo POR EJECUTAR.** El mecanismo está implementado y congelado, pero
el reporte numérico todavía NO se ha corrido: ninguno de los números de
este documento fue producido por una ejecución real. NO fabricarlos.

## Método

1. **Corpus congelado** (`corpus/manifest.csv`, 20 textos):
   10 humanos (h01..h10, dominio público, Project Gutenberg, corte manual
   desde 30% del cuerpo; sin alterar palabras; 24-oct-2026) y 10 generados
   por Hermes Agent (modelo glm-5.3-flash via opencode-go; 10 prompts
   narrativos distintos, uno por archivo; con uso de investigación;
   redistribución libre).
2. **Split por GRUPOS** (unidad = autor/obra humano; prompt/pieza IA;
   una pieza por grupo):
   - `HOLDOUT = {h03, h04, h08, a05, a09}` (3 humanos + 2 IA; una pieza
     por grupo: la unidad de split es el GRUPO, nunca el comando a mano).
   - Resto = `TRAIN` (h01, h02, h05, h06, h07, h09, h10, a01..a04, a06..a08,
     a10 — 15 casos).
   - El holdout NO aporta semillas: `corpus/seeds/seed_ia_es.txt` y
     `seed_hum_es.txt` son concatenaciones exactas (unidas por `\n\n`) de los
     textos de TRAIN de su clase, verificadas por checksum. Los tests
     (`tests/test_calibration.py`) comprueban que ningún holdout contiene
     subcadenas de 50 chars de ninguna semilla.
3. **Barrido y validación SOLO con TRAIN**:
   - Barrido determinista de `(umbral, margen)` sobre `AREA_UMBRAL =
     range(0, 101)` y `MARGENES = (0, 2, 4, 6, 8)`.
   - Validación cruzada **leave-one-group-out (LOgo-CV)** dentro de TRAIN:
     el umbral/margen de cada fold se elige con el resto de TRAIN; los
     grupos del holdout nunca participan.
   - Criterio de elección: máximo balanced accuracy; desempates
     deterministas (menor margen, luego menor `|umbral − 50|`)
     (`calibrate._elegir` / `_mejor`).
   - El umbral/margen FINAL se emite con TODO el train (nunca con holdout).
4. **Puntuación F2 congelada**: cada texto pasa por los 5 checks
   (burstiness, mattr, uniformity, cliches_es, compression) +
   `scoring.compute_indice`. La calibración NO retoca pesos ni
   transformaciones.
5. **HOLDOUT se abre UNA VEZ** (solo desde `main()`): matriz TP/FP/TN/FN,
   tasa de FPs sobre humanos y abstenciones. Los tests no lo invocan.

Predicción con abstención: banda centrada en el umbral de ancho
`margen`; `|indice − umbral| <= margen` ⇒ abstención.

## Resultados (placeholders; rellenar tras ejecutar `python -m tools.calibrate`)

| Métrica | Valor |
|---|---|
| Umbral final | POR EJECUTAR |
| Margen final | POR EJECUTAR |
| CV TPR media (LOgo) | POR EJECUTAR |
| CV TNR media (LOgo) | POR EJECUTAR |

Matriz del HOLDOUT (UNA apertura):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **VIA IA (a05, a09)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |
| **Real humano (h03, h04, h08)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |

Tasa de FP sobre humanos: POR EJECUTAR

## Limitaciones

- **N extremadamente pequeño**: 20 textos, 5 en holdout. Cualquier número
  de esta calibración tiene incertidumbre enorme; NO extrapolar.
- **Desbalance de procedencia**: los textos IA provienen de UN modelo y UN
  agente en UNA sola familia de prompts narrativos; el índice NO se ha
  calibrado contra otros modelos, idiomas ni géneros.
- **Corte manual de humanos** (30% del cuerpo): subjetivo; no se prueba
  robustez a otros puntos de corte aunque el corpus congela este.
- **Check compression congelado con fixtures sintéticas**: las semillas
  reales quedan construidas y verificadas por checksum para el wiring
  posterior; el check aún NO está retazado contra textos humanos reales.
- **LOgo-CV con una pieza por grupo**: la CV dentro de train es
  leave-one-OUT-pieza; su estimación optimista/bidón no se cuantifica.
- **Textos cortos y abstención**: la banda de abstención existe para
  textos límite, pero hay que reportar también los NO abstenciones (tasas
  condicionadas al no abstenerse), no solo los aciertos brutos.
- Uso previsto: AYUDA A LA REVISIÓN HUMANA. Nunca filtro automático
  sin humano en decisión.

## Reproducibilidad

- `cargar_corpus()` es determinista (orden del manifest, sin azar); los
  tests comparan 2 cargas por SHA256 del informe en memoria.
- Correr una vez (abre el holdout): `python -m tools.calibrate` (o
  `python tools/calibrate.py` desde la raíz del repo). Reporte JSON con
  claves ordenadas.
