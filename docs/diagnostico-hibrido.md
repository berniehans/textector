# Diagnóstico híbrido (prosa × estructura)

## Marco honesto: dos ejes separados

El resultado del pipeline F2 (`indice_llm`) mide solo la **PROSA**:
estilo de frase, léxico, esquematismo lexicalizado. El nuevo bloque
(`tools/estructura.py`) mide solo la **ESTRUCTURA**: el esqueleto
documental — secciones numeradas `S01...`, reparto de tamaños, párrafos
por sección y proporción de diálogo. El diagnóstico híbrido
(`tools/diagnostico.py`) cruza ambos ejes, pero **no fusiona las
señales en un número nuevo** y no altera ningún peso ni transformación
congelados en F2.

Por qué dos ejes: existe un caso real que el índice de prosa **no puede
detectar con features de superficie** — texto hoy escrito por una
persona con estructura propia (boceto, jerarquía irregular, escenas
desigualadas) cuyos párrafos finales fueron reescritos o expandidos por
un LLM. La prosa resulta marcada (o no, según el rewrite), pero la
estructura no se parece al esqueleto clónico de una plantilla: el
reparto de secciones falta o sobra de forma que NO concluye por sí solo
para las métricas de prosa. Un
índice único mezclaría ambos motores de señal y daría la ilusión de un
veredicto; separando los ejes, el diagnóstico admite la combinación
«estructura propia + prosa IA» como categoría propia — sin pretender
probarla.

Lo que NO se alcanza a detectar con features de superficie: el caso
«humano en la estructura + prosa IA en proporción baja» solo asoma como
«intermedia/irregular + banda de prosa»; esa combinación queda
deliberadamente en `prosa_no_concluyente`.

## Banda de abstención de prosa (congelada F3)

- `UMBRAL = 26`, `MARGEN = 8` (los mismos que usó la calibración F3).
- Banda: `18 <= indice_llm < 26` → señal débil, no concluyente.
- `indice_llm >= 26` → ranura "marcada"; `<= 18` → "sin señal".

## Tabla de categorías

| prosa | estructura | categoría | no_concluyente |
|---|---|---|---|
| >= 26 | regular (>= 60) | `plantilla_prosa_y_estructura` | False |
| >= 26 | irregular (<= 40) | `probable_hibrido_estructura_propia_prosa_ia` | True |
| >= 26 | intermedia / insuficiente | `prosa_no_concluyente` | True |
| 18..25 | cualquiera | `prosa_no_concluyente` (+ nota de estructura) | True |
| <= 18 | irregular | `sin_senal_suficiente` | True |
| <= 18 | regular | `estructura_regular_prosa_no_marcada` | True |
| <= 18 | intermedia / insuficiente | `prosa_no_concluyente` | True |

`no_concluyente` es **True en todas las categorías salvo**
`plantilla_prosa_y_estructura` (plantilla pura, el único patrón con base
para afirmar "consistente con texto generado").

## Fronteras del eje estructura (`tools/estructura.regularidad`)

Regularidad = media de 3 CVs monótonos + bonus, en [0, 1]:

1. **CV de largos de sección (chars)**: tramo [0.05, 0.60]. CV <= 0.05
   (secciones clónicas) → 1.0; CV >= 0.60 (razones >= 4:1) → 0.0.
2. **CV de párrafos por sección**: tramo [0.15, 0.80] — más laxo porque
   un párrafo extra en sección corta mueve el CV mucho; 0.80 ~ secciones
   de 1 vs 10 párrafos.
3. **CV del ratio de diálogo entre secciones**: tramo [0.10, 0.50].
   Sin diálogo en ninguna sección → componente 0.5 NEUTRAL (no inventa
   señal).
4. **Bonus +0.05** si la numeración es consecutiva desde `S01`
   (plantillas numeran así). Total acotado a [0, 1].

`valor` = round(regularidad × 100). Etiquetas: >= 60 «regular»,
<= 40 «irregular», 41..59 «intermedia»; sin secciones →
`insufficient` (sin base: valor 0, no puntúa).

## Límites (leer antes de usar)

- El eje estructura NO está calibrado contra corpus: las fronteras de CV
  son decisiones de diseño documentadas, no umbrales empíricos. Es
  heurística no probatoria.
- La detección de secciones exige el formato `S\d+` (con o sin `#` y
  separador): otros esqueletos (I., 1., A.) no se detectan y degradan a
  `insufficient` — eso es abstención honesta, no error.
- El eje prosa hereda límites F3: pre-filtro de dominio/estilo, 0 falsos
  positivos en prosa clásica del holdout NO significa exculpación.
- Nada de esto es prueba de autoría. `no_concluyente` es su estado
  natural; solo la plantilla pura pasa a "concluyente", y aun así es un
  indicio.

## Ejemplo de salida

```json
{
  "prosa": {
    "indice_llm": 38,
    "banda_abstencion": {"umbral": 26, "margen": 8, "cota_inferior": 18, "cota_superior": 26}
  },
  "estructura": {
    "valor": 88,
    "etiqueta": "regular",
    "regularidad": 0.8833,
    "n_secciones": 6,
    "insufficient": false
  },
  "categoria": "plantilla_prosa_y_estructura",
  "nota": "Prosa con señal marcada de LLM y estructura regular tipo plantilla: patrón consistente con texto generado por IA. Es la única categoría concluyente del diagnóstico.",
  "no_concluyente": false
}
```

Añadir al CLI: `--diagnostico` imprime el bloque (y con `--json` se añade
como clave `diagnostico` sin tocar el resto del informe).
