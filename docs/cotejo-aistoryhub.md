> **Estado tras f4-integridad:** el cotejo que sigue es un registro histórico.
> Todas las antiguas etiquetas `aich::` se renombraron a
> `inspiracion-tematica::`, sin cambiar frases ni pesos. No se afirma derivación
> 1:1 ni se volvió a verificar el corpus externo. En el resumen histórico, las
> 3 espurias son los dos “No” con match descartado y la fila “Dudoso”; las 8
> inexistentes son las otras filas “No”. Una de las 3 correspondencias
> reportadas es aproximada, como indica su fila.

# Cotejo AIStoryHub (F8c) — resultado real

Fuente descargada: `AIStoryHub/AIStoryHub_LLM_Cliche_Corpus`,
`ai-cliches-corpus.json`, **versión 1.7, 758 entradas** en seis categorías
(`words_and_phrases`, `sentence_patterns`, `rhetorical_moves`, `formatting_tells`,
`names_and_personas`, `channel_and_assistant`), cada una con `strength_score`
0–100 y tier de confianza.

Cotejo ejecutado el 2026-10-25 sobre `config/cliches_es.yaml`
(**25 entradas**: 14 con etiqueta `aich::` y 11 `es-nativo`).

## Veredicto en una línea

**La atribución al corpus es temática, no 1:1.** De las 14 entradas etiquetadas
`aich::`, solo **3 tienen correspondencia verificable** con un término del
corpus; **8 no existen** en el corpus y **3 más** solo coinciden por parecido
superficial (falsos positivos del emparejamiento difuso, descartados).

## Detalle

| Frase ES (léxico) | Peso | Slug declarado | ¿En corpus v1.7? | Término real | `strength_score` |
|---|---|---|---|---|---|
| sumérgete en | 40 | `immerse` | **Sí** | `immerse` | 75 |
| al fin y al cabo | 18 | `at-the-end-of-the-day` | **Sí** | `At the end of the day` | 75 |
| más importante que nunca | 30 | `more-important-than-ev…` | **Sí** (aprox.) | `more importantly` | 50 |
| en el fondo | 26 | `at-heart` | Dudoso | el match difuso (`in the heart of`) es otro sentido | 50 |
| sus labios se curvaron | 30 | `lips-curve` | **No** | — (el match `discourse` es espurio) | — |
| el destino estaba sellado | 30 | `destiny-sealed` | **No** | — (el match `delineate` es espurio) | — |
| en un mundo donde | 45 | `world-of` | **No** | — | — |
| no es solo __, es __ | 38 | `not-only-is` | **No** | — | — |
| la puerta se abrió de par en par | 15 | `door-swing-open` | **No** | — | — |
| una mezcla de __ y __ | 20 | `mixture-of-fear-love` | **No** | — | — |
| todo cambió en ese momento | 26 | `everything-changed` | **No** | — | — |
| soltó una risa | 22 | `chuckle-release` | **No** | — | — |
| como una conspiración | 35 | `like-conspiracy` | **No** | — | — |
| pequeños detalles que | 22 | `small-details` | **No** | — | — |

Resumen numérico: **14 etiquetas `aich::` · 3 verificables · 8 inexistentes ·
3 espurias**. Las 11 entradas `es-nativo` son señal narrativa ES propia
(revisión manual F2), sin relación con el corpus.

## Consecuencias

1. **`NOTICE` no puede afirmar** que las frases «derivan» del corpus entrada por
   entrada: la relación real es *inspiración temática* sobre las categorías de
   ficción, con 3 correspondencias verificadas. Se corrige la redacción.
2. **Ninguna entrada del léxico se elimina ni se re-pondera** por este cotejo:
   los pesos están congelados (F2) y el cotejo mide procedencia, no conducta.
3. **Los `strength_score` del corpus no son comparables** con nuestros pesos
   0–100: miden fortaleza de detección en inglés, no densidad ES por 1000
   tokens. No se trasladan.
4. Queda como mejora futura (F8c completo) re-etiquetar cada frase con su
   término real cuando exista, o marcarla explícitamente como `es-nativo`.

## Reproducibilidad

```bash
curl -sSL -o aich.json \
  https://raw.githubusercontent.com/AIStoryHub/AIStoryHub_LLM_Cliche_Corpus/main/ai-cliches-corpus.json
# 758 entradas, version 1.7
```
Emparejamiento: normalización del slug (`-`→espacio), búsqueda exacta y, si
falla, `difflib.get_close_matches(cutoff=0.6)`; los aproximados se revisan a
mano y se descartan si el sentido no coincide (como ocurrió con 3 de ellos).
