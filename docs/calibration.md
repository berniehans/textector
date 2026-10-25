# Calibración F3-v2 de textector — `tools/calibrate.py`

> **Estado: EXPERIMENTAL.** Todo lo que sale de esta calibración es un
> **índice heurístico, NO probatorio**: no es probabilidad, no es prueba de
> autoría ni evidencia legal. Ver `pyproject.toml` (descripción del
> proyecto) y `docs/methodology.md`.

## Estado de ejecución

**EJECUTADO (dos versiones, una apertura por señal).** v2 (señal f2) se
ejecutó el 24-oct-2026 y el planner la verificó el 25-oct. La v3 (señal
`f3-semillas`) la ejecutó el maestro tras F5; reporte crudo en
`.hermes/evidence/f6-calib-v3.json` (exit 0), fuente de todos los números
v3 de este documento. La apertura #2 del holdout es única para
`f3-semillas` y estuvo justificada por el cambio de señal f2 →
`f3-semillas`; la #1 (24-oct) fue la de v2. Ambas aperturas están
consumidas. La re-ejecución debe reproducir los campos clave de los
reportes (umbral, margen, matriz, tasas, abstenciones).

## Método v2

1. **Corpus congelado** (`corpus/manifest.csv`, 40 piezas en 3 subcarpetas):
   - `human/h01..h20.txt` — 20 humanos de dominio público (Project
     Gutenberg, corte manual desde 30% del cuerpo; sin alterar palabras;
     24-oct-2026). Cada fila con SHA256 en el manifest.
   - `llm/a01..a10.txt` — 10 narrativa IA propia generada por Hermes Agent
     (modelo glm-5.3-flash via opencode-go; 10 prompts narrativos
     distintos, uno por archivo; con uso de investigación;
     redistribución libre).
   - `news/b01..b10.txt` — 10 noticias sintéticas de SLM (Zenodo DOI
     19449815, pipeline del art. MDPI DATA 11(2):29; CC-BY-4.0). En el
     schema interno la **clase es `llm`** (es texto de IA) y el campo
     añadido **`dominio`** distingue `narrativa_propia` (a*) de
     `noticias_sinteticas` (b*).
2. **Split por GRUPOS v2** (unidad = AUTOR humano; pieza IA; grupo):
   - **Grupos humanos**: h14 == h17 (Pereda, mismo grupo); h11 (pg15532,
     P. A. de Alarcón) grupo propio; h12 Fernán Caballero; h13 Coloma;
     h14+h17 Pereda; h15 Picón; h16 Alas/Clarín; h18 J. Ruiz de Alarcón
     (Siglo de Oro, NO es el mismo autor que h11); h19 Zorrilla; h20
     Escosura. h01..h10 mantienen su autor propio (nota: h08 y h16
     comparten autor (Alas/Clarín) y grupo, pero ambos caen en holdout).
   - **Grupos IA**: a01..a10, un grupo por id de archivo; b01..b10 UN
     solo grupo (`zenodo`, mismo generador).
   - **HOLDOUT_V2 (FIJO, elegido ya; no cambia): {h08, h16, h19, a05,
     a07, b03}** (3 humanos + 3 IA). Resto = TRAIN (34 casos).
   - El holdout NO aporta semillas: `corpus/seeds/seed_ia_es.txt` es
     concatenación exacta (unida por `\n\n`) de los textos IA de TRAIN;
     con el holdout_v2 se retiró el bloque de a07 (a05 ya estaba fuera).
     Los tests (`tests/test_calibration.py`) comprueban que ningún texto
     del holdout contiene subcadenas de 50 chars de ninguna semilla.
3. **Barrido y validación SOLO con TRAIN**:
   - Barrido determinista de `(umbral, margen)` sobre `AREA_UMBRAL =
     range(0, 101)` y `MARGENES = (0, 2, 4, 6, 8)`.
   - Validación cruzada **LOGO-CV (leave-one-group-out)** dentro de TRAIN:
     el umbral/margen de cada fold se elige con el RESTO de TRAIN; el
     holdout nunca participa. Folds reales: se deja fuera todo el grupo
     Pereda (h14+h17) y todo el grupo Zenodo (los b de train).
   - Criterio de elección: máximo balanced accuracy; desempates
     deterministas (menor margen, luego menor `|umbral − 50|`)
     (`calibrate._elegir` / `_mejor`).
   - El umbral/margen FINAL se emite con TODO el train (nunca con holdout).
4. **Puntuación F2 congelada**: cada texto pasa por los 5 checks
   (burstiness, mattr, uniformity, cliches_es, compression) +
   `scoring.compute_indice`. La calibración NO retoca pesos ni
   transformaciones. v3 re-ejecuta esta misma mecánica tras el wiring
   F5: constantes `VERSION_METODO = "f3-semillas"` y semillas
   `reales-es`; los pesos permanecen congelados y la calibración solo
   ajusta umbral y margen.
5. **HOLDOUT_V2 se abre UNA VEZ** (solo desde `main()`): matriz
   TP/FP/TN/FN, **tasa de FPs sobre humanos**, **tasa de FNs sobre IA**,
   **desglose de FPs por subtipo humano** (clásicos vs modernos),
   **desglose de FNs por dominio IA** (narrativa propia vs noticias) y
   **abstenciones visibles** (ids). Los tests no lo invocan.

   Subtipos humanos (constante `CLASICOS`, definición explícita en
   `tools/calibrate.py`): *clásicos* = Siglos de Oro (XVI-XVII): h01
   Cervantes, h02 Lazarillo (anónimo), h03 Quevedo, h18 J. Ruiz de
   Alarcón. *Modernos* = restantes (XVIII-XIX).

Predicción con abstención: banda centrada en el umbral de ancho
`margen`; `|indice − umbral| <= margen` ⇒ abstención.

## Resultados v2 — señal f2 (histórica, NO comparable con v3)
(ejecutados una sola vez el 24-oct-2026, 23:0x)

| Métrica | Valor |
|---|---|
| Umbral final | 26 |
| Margen final | 8 |
| CV TPR media (LOGO, TRAIN) | 0.04 |
| CV TNR media (LOGO, TRAIN) | 0.24 |

> **Nota honesta:** la elección in-sample del umbral reportó TPR 0.857 / TNR 1.0,
> pero la validación leave-one-group-out en TRAIN —la señal honesta de
> generalización— da TPR 0.04 y TNR 0.24. El índice apenas separa en español.

Matriz del HOLDOUT_V2 (UNA apertura):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **Real IA (a05, a07, b03)** | 0 | 2 | 1 |
| **Real humano (h08, h16, h19)** | 0 | 1 | 2 |

Desglose de FP por subtipo humano:

| Subtipo | FPs del holdout_v2 |
|---|---|
| clasicos (h01/h02/h03/h18) | 0 |
| modernos (h08/h16/h19) | 0 |

Desglose de FN por dominio IA:

| Dominio | FNs del holdout_v2 |
|---|---|
| narrativa_propia (a*) | 2 (a05 índice 16, a07 índice 17 → "humano") |
| noticias_sinteticas (b*) | 0 (b03 índice 29 → abstención) |

Tasas: FP/humano-no-abstención = 0/1 = 0.0; FN/IA = 2/3 ≈ 0.67.
Abstenciones del holdout_v2: `b03`, `h08`, `h19`.

**Lectura del resultado:** cero falsos positivos en literatura clásica (el fallo
de v1 desapareció), pero **el índice no detecta la narrativa IA**: los dos FNs son
textos IA de la clase narrativa propia, y la única pieza de noticias sintéticas cae
en abstención. El patrón de índices del TRAIN lo confirma: noticias `b*` puntúan
32–38 y la narrativa IA `a*` 16–27, solapándose con la literatura humana.
Conclusión de rol: **pre-filtro de dominio/estilo, no detector de autoría**;
cualquier uso debe tratar "humano" como "sin señal suficiente", no como exculpación.

## Resultados v3 — señal f3-semillas (apertura #2 del holdout)

Fuente: `.hermes/evidence/f6-calib-v3.json` (ejecución real del maestro
tras F5, exit 0). Señal: check compression retazado con semillas ES
reales (`f3-semillas`).

Elección TRAIN (LOGO-CV, 34 piezas):

| Métrica | Valor |
|---|---|
| Umbral final | 31 |
| Margen final | 2 |
| Elección in-sample: TPR / TNR / BAL | 1.0 / 0.9333 / 0.9667 |
| CV TPR media (LOGO, TRAIN) | 0.24 (v2: 0.04) |
| CV TNR media (LOGO, TRAIN) | 0.54 (v2: 0.24) |

> **Nota honesta:** la elección in-sample (TPR 1.0 / BAL 0.9667) es
> optimista: se mide sobre los mismos casos que eligieron el umbral. La
> señal honesta de generalización es la CV, y es modesta: TPR 0.24 /
> TNR 0.54 (mejor que la CV de v2, lejos de un clasificador usable).

Matriz del holdout (apertura #2, única para `f3-semillas`):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **Real IA (a05, a07, b03)** | 0 | 3 | 0 |
| **Real humano (h08, h16, h19)** | 0 | 2 | 1 |

Casos con índice:

| Id | Índice | Real | Predicho | Resultado |
|---|---|---|---|---|
| a05 | 17 | ia | humano | FN |
| a07 | 20 | ia | humano | FN |
| b03 | 28 | ia | humano | FN |
| h08 | 26 | humano | humano | TN |
| h16 | 14 | humano | humano | TN |
| h19 | 29 | humano | abstención | abstención |

Desglose de FN por dominio IA:

| Dominio | FNs del holdout v3 |
|---|---|
| narrativa_propia (a*) | 2 (a05, a07) |
| noticias_sinteticas (b*) | 1 (b03) |

Desglose de FP por subtipo humano:

| Subtipo | FPs del holdout v3 |
|---|---|
| clasicos (h01/h02/h03/h18) | 0 |
| modernos (h08/h16/h19) | 0 |

Tasas condicionadas: FP/humanos-no-abstenidos = 0/2 = 0.0; FN/IA =
3/3 = 1.0. Abstenciones del holdout v3: `h19` (índice 29).

Patrón de índices TRAIN v3: b* entre 31 y 37; a* entre 29 y 43 (a02 43,
a04 41, a08 41, a03 40, a10 35, a01 33, a06 32, a09 29); humanos bajos
salvo **h14 = 54**, único caso sobre el umbral in-sample (el FP que
descuadra TNR 0.9333).

Comparativa breve, etiquetada por versión. **NO es apples-to-apples: la
señal del índice cambió de f2 a `f3-semillas`**, y cada columna usa SU
propia apertura del holdout (#1 v2, #2 v3):

| Métrica | v2 (señal f2; apertura #1) | v3 (f3-semillas; apertura #2) |
|---|---|---|
| Umbral / margen | 26 / 8 | 31 / 2 |
| CV TPR media (LOGO, TRAIN) | 0.04 | 0.24 |
| CV TNR media (LOGO, TRAIN) | 0.24 | 0.54 |
| Holdout TP / FN (IA) | 0 / 2 | 0 / 3 |
| Holdout FP / TN (humano) | 0 / 1 | 0 / 2 |
| Abstenciones del holdout | 3 | 1 |

**Conclusión sin spin:** v3 mejora la CV respecto de v2 (TPR 0.24 y
TNR 0.54 contra 0.04 y 0.24), pero en el holdout TP = 0 (FN/IA = 1.0) →
**NO es un clasificador de autoría**. El rol correcto sigue siendo
**pre-filtro heurístico con abstención**: "humano" significa "sin señal
suficiente", **NO es exculpación**. Con n = 6 y las DOS aperturas del
holdout ya consumidas (una por señal), esta evaluación no tiene potencia
estadística; la única evidencia positiva es la CV modesta dentro de
train.

## Histórico v1 (declarado como tal; NO es el método activo)

> **Histórico v1**: el corpus original tenía 20 textos (h01..h10 +
> a01..a10) con `HOLDOUT = {h03, h04, h08, a05, a09}` y grupos de una
> sola pieza por autor. Este holdout **sí se evaluó una vez** en la fase
> F3, pero su registro (`.hermes/plans/evidencia-final-f1-f4.md`) es
> internamente inconsistente —anota «TP=2, FN=0, FP=3, TN=0, abstención=1»
> para 5 piezas, es decir 6 predicciones— y no es reproducible con el
> código actual (corpus, split y señal cambiaron a `f3-semillas`). Por
> eso la matriz v1 se conserva **sin cifras** (`—`) y no se reconstruye
> aquí. El método activo es v3 (arriba); v1 no es comparable.

Matriz del HOLDOUT v1 (histórico, no reconstruible con la evidencia disponible):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **Real IA (a05, a09)** | — | — | — |
| **Real humano (h03, h04, h08)** | — | — | — |

Tasa de FP sobre humanos (v1): — (no reconstruible; ver nota anterior).

## Limitaciones v2

- **N pequeño y holdout de 6**: 40 piezas, 6 en holdout (3 por clase).
  Cualquier número del holdout_v2 tiene incertidumbre enorme; NO
  extrapolar. CV de train (34) solo aproxima.
- **Tensión de grupo Zenodo**: b03 (holdout) pertenece al grupo b01..b10
  y el resto de su grupo está en TRAIN. El umbral se elige con noticias
  del MISMO generador y pipeline que b03: el aislamiento por autor
  completo no es posible con este split v2 (limitación declarada, no un
  error de implementación).
- **Desbalance de procedencia**: los a* provienen de UN modelo y UN
  agente en UNA sola familia de prompts narrativos; los b* de UN pipeline
  SLM Zenodo. El índice NO se ha calibrado contra otros modelos, idiomas,
  géneros ni noticias humanas reales (no hay news humanas en el corpus).
- **Corte manual de humanos** (30% del cuerpo): subjetivo; no se prueba
  robustez a otros puntos de corte aunque el corpus congela este.
- **Check compression retazado con semillas ES reales** (F5): las
  semillas quedan etiquetadas `reales-es` y el modo falla cerrado si
  faltan. Consecuencias: los índices de v3 NO son comparables con los de
  v2 (señal distinta: f2 vs `f3-semillas`), y el holdout ya consumió sus
  DOS aperturas (una por señal: #1 f2 el 24-oct, #2 `f3-semillas`); un
  cambio futuro de señal exige corpus y holdout nuevos (F8).
- **LOGO-CV con grupos mayoritariamente de una pieza**: para casi todos
  los grupos la CV dentro de train es leave-one-OUT-pieza; su estimación
  optimista/bidón no se cuantifica.
- **Clásicos vs modernos es una partición autoral** (siglo del autor),
  no una validación empírica de estilo por época.
- **Textos cortos y abstención**: la banda de abstención existe para
  textos límite, pero hay que reportar también los NO abstenciones (tasas
  condicionadas al no abstenerse), no solo los aciertos brutos.
- Uso previsto: AYUDA A LA REVISIÓN HUMANA. Nunca filtro automático
  sin humano en decisión.

## Reproducibilidad

- `cargar_corpus()` es determinista (orden del manifest, sin azar); los
  tests comparan 2 cargas por SHA256 del informe en memoria (40 piezas,
  3 subcarpetas, campo `dominio` incluido).
- Correr una vez: `python -m tools.calibrate` (o `python
  tools/calibrate.py` desde la raíz del repo). Ahora requiere
  `corpus/seeds` (fail-closed si faltan). La re-ejecución con el mismo
  corpus y la misma señal reproduce el reporte determinista (JSON con
  claves ordenadas). Las aperturas #1 (f2) y #2 (`f3-semillas`) del
  holdout ya están consumidas: nuevas aperturas del MISMO holdout NO
  añaden validez; validar una señal nueva exige corpus nuevo (F8).
- Tests (no puntúan el holdout): `python -m unittest tests.test_calibration`
  desde la raíz del repo.
