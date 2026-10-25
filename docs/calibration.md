# Calibración F3-v2 de textector — `tools/calibrate.py`

> **Estado: EXPERIMENTAL.** Todo lo que sale de esta calibración es un
> **índice heurístico, NO probatorio**: no es probabilidad, no es prueba de
> autoría ni evidencia legal. Ver `pyproject.toml` (descripción del
> proyecto) y `docs/methodology.md`.

## Estado de ejecución

**Archivo POR EJECUTAR.** El mecanismo v2 está implementado y congelado,
pero el reporte numérico todavía NO se ha corrido: ninguno de los números
de este documento fue producido por una ejecución real. NO fabricarlos.

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
   transformaciones.
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

## Resultados v2 (placeholders; rellenar tras ejecutar `python -m tools.calibrate`)

| Métrica | Valor |
|---|---|
| Umbral final | POR EJECUTAR |
| Margen final | POR EJECUTAR |
| CV TPR media (LOGO) | POR EJECUTAR |
| CV TNR media (LOGO) | POR EJECUTAR |

Matriz del HOLDOUT_V2 (UNA apertura):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **Real IA (a05, a07, b03)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |
| **Real humano (h08, h16, h19)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |

Desglose de FP por subtipo humano:

| Subtipo | FPs del holdout_v2 |
|---|---|
| clasicos (h01/h02/h03/h18) | POR EJECUTAR |
| modernos (resto) | POR EJECUTAR |

Desglose de FN por dominio IA:

| Dominio | FNs del holdout_v2 |
|---|---|
| narrativa_propia (a*) | POR EJECUTAR |
| noticias_sinteticas (b*) | POR EJECUTAR |

Tasas condicionadas (FP/humano no abstención; FN/IA): POR EJECUTAR.
Abstenciones del holdout_v2 (ids, visibles en el reporte JSON bajo
`abstenciones_ids`): POR EJECUTAR.

## Histórico v1 (declarado como tal; NO es el método activo)

> **Histórico v1**: el corpus original tenía 20 textos (h01..h10 +
> a01..a10) con `HOLDOUT = {h03, h04, h08, a05, a09}` y grupos de una
> sola pieza por autor. La matriz v1 siguiente conserva los placeholders
> del esquema v1, **que nunca llegó a ejecutarse**: sus números NO
> existen. Se conservan como constancia histórica y NO corresponde
> completarlos (el método activo es el v2 de arriba; corpus y split son
> distintos, no hay comparación apples-to-apples).

Matriz del HOLDOUT v1 (histórico, NUNCA ejecutado):

| | Predicho IA | Predicho humano | Abstención |
|---|---|---|---|
| **Real IA (a05, a09)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |
| **Real humano (h03, h04, h08)** | POR EJECUTAR | POR EJECUTAR | POR EJECUTAR |

Tasa de FP sobre humanos (v1): POR EJECUTAR.

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
- **Check compression congelado con fixtures sintéticas**: la semilla IA
  se actualizó para el split v2 (sin los bloques de a05/a07), pero el
  check aún NO está retazado contra textos reales; wiring pendiente.
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
- Correr una vez (abre el holdout_v2): `python -m tools.calibrate` (o
  `python tools/calibrate.py` desde la raíz del repo). Reporte JSON con
  claves ordenadas.
- Tests (no puntúan el holdout): `python -m unittest tests.test_calibration`
  desde la raíz del repo.
