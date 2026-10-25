# Referencia de checks — textector

Todos los valores de este documento están **congelados** (F2). Cambiarlos exige
recalibrar y actualizar `docs/methodology.md`.

## Score

```
contribucion_i = 100 · w_i · q_i / Σ w_disponibles
indice_llm     = round(Σ contribucion_i)
```

- `q_i` ∈ [0,1]: transformación monótona propia de cada check (abajo).
- Si un check queda `insufficient`, **sale de la suma y el resto renormaliza**.
- Si faltan checks para cubrir el pipeline (5/5), el CLI aborta con
  «texto muy corto» y **no emite número**.

## Pesos y topes de grupo

| Check | Peso |
|---|---|
| `cliches_es` | 0.24 |
| `compression` | 0.23 |
| `burstiness` | 0.18 |
| `uniformity` | 0.18 |
| `mattr` | 0.17 |

Topes de peso conjunto (checks correlacionados, para que no dominen en bloque):

| Grupo | Tope Σw |
|---|---|
| `mattr` + `burstiness` | 0.32 |
| `cliches_es` + `uniformity` | 0.40 |

## 1. `burstiness` — dispersión de longitudes de oración

- **Qué mide**: CV robusto (mediana/MAD) de la longitud léxica de las oraciones.
  Prosa humana suele variar más; la generada tiende a un ritmo uniforme.
- **Mínimo**: `MIN_ORACIONES = 10` (menos → `insufficient`).
- **Transformación**: `q = clamp(1 − (cv − 0.20) / (0.60 − 0.20))`
  → CV ≤ 0.20 ⇒ q=1 (uniforme, señal LLM); CV ≥ 0.60 ⇒ q=0 (muy variable).
- **Límites**: el diálogo corto baja artificialmente el CV; se reporta
  `n_dialogo` como apoyo explicativo.

## 2. `mattr` — diversidad léxica en ventana

- **Qué mide**: MATTR (moving-average TTR) con ventana fija de **50 tokens**.
- **Mínimo**: ≥ 50 tokens (si no, `insufficient`; nunca se sustituye por TTR simple).
- **Transformación**: `q = clamp(1 − (mattr − 0.55) / (0.85 − 0.55))`
  → MATTR bajo ⇒ q alto. Texto muy corto no es comparable.

## 3. `uniformity` — ritmo de párrafos y repetición

- **Qué mide**: (a) dispersión de largos de párrafo; (b) repetición de
  conectores/aperturas de oración (share del más frecuente).
- **Mínimo**: `MIN_PARRAFOS = 3`.
- **Transformación**: `q = (q_dispersion + q_repeticion) / 2`, con
  `q_disp = clamp(1 − (cv − 0.15) / (0.40 − 0.15))` y
  `q_rep = clamp((share − 0.22) / (0.55 − 0.22))`.
- **Frontera ajustada en el gate F2**: `CV_MAX` bajó de 0.60 a **0.40**
  (ejemplo ES en `docs/methodology.md` §3).

## 4. `cliches_es` — léxico de clichés LLM en español

- **Qué mide**: hits del léxico YAML-min (frases y conectores plantilla)
  ponderados por su `peso` y normalizados por volumen:
  `densidad_ponderada_por_1000 = Σ pesos_hit / n_tokens · 1000`.
- **Mínimo**: `MIN_TOKENS = 50`.
- **Transformación**: `q = clamp(densidad / 2.5)` (densidad 2.5‰ ⇒ q=1).
- **Léxico**: `config/cliches_es.yaml`, editable; derivado del corpus MIT
  *AIStoryHub LLM Cliche Corpus* + señales narrativas ES propias (ver `NOTICE`).
- **Límites**: un cliché aislado no dice nada; la señal es la densidad.

## 5. `compression` — predecibilidad por compresión sembrada

- **Qué mide**: raw DEFLATE (`zlib.compressobj(level=6, wbits=-15)`) sobre el
  texto normalizado, comparando el **delta** de compresión con la semilla IA y
  con la semilla humana (método portado de `thinkst/zippy`, MIT).
  `delta = m_ia − m_h` (positivo ⇒ comprime mejor contra la semilla IA).
- **Semillas**: `corpus/seeds/seed_ia_es.txt` y `seed_hum_es.txt` (**solo
  train**, nunca holdout; nunca semillas inglesas).
- **Mínimo**: `MIN_BYTES_MUESTRA = 150`.
- **Transformación**: `q = clamp(0.5 − delta / 0.40)`
  → delta 0 ⇒ q=0.5 (neutro); delta ≥ 0.20 ⇒ q=0.
- **Límite documentado**: el valor **no** es invariante a la longitud; se
  interpreta **direccionalmente** con el umbral calibrado en F3.

## Eje estructural (`--diagnostico`)

No forma parte del score. `tools/estructura.py` mide el esqueleto del documento:

- Detección de cabeceras `S\d+` (con/sin `#`, con separador `— – : -`).
- CV de largos por sección, CV de párrafos por sección, CV del ratio de diálogo.
- Bonus por cabeceras numeradas presentes.
- `regularidad` ∈ [0,1]; `valor = round(100·regularidad)`.
  Etiquetas: **regular ≥ 60**, **irregular ≤ 40**, intermedia en medio;
  sin secciones detectadas → `insufficient`.

## Tabla de categorías del diagnóstico

| Prosa | Estructura | Categoría | Concluyente |
|---|---|---|---|
| ≥ 26 | regular | `plantilla_prosa_y_estructura` | **Sí** |
| ≥ 26 | irregular | `probable_hibrido_estructura_propia_prosa_ia` | No |
| 18–26 (banda) | cualquiera | `prosa_no_concluyente` | No |
| ≤ 18 | irregular | `sin_senal_suficiente` | No |
| ≤ 18 | regular | `estructura_regular_prosa_no_marcada` | No |

`no_concluyente=True` en todas salvo la primera. La nota del diagnóstico
recuerda que «estructura regular» puede ser un formato de trabajo propio
(escenas numeradas) y no una plantilla generada.
