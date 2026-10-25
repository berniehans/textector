# Corpus — composición, procedencia y reglas

## Composición actual (v2, 40 piezas)

| Clase | Carpeta | N | Origen | Licencia |
|---|---|---|---|---|
| Humano literario | `corpus/human/h01..h20.txt` | 20 | Project Gutenberg ES, dominio público (Cervantes, Lazarillo, Quevedo, Palma, Pardo Bazán, Galdós, Valera, Clarín, Bécquer, Larra, Alarcón, Fernán Caballero, Coloma, Pereda, Picón, Zorrilla, Escosura) | Dominio público, redistribución libre |
| IA narrativa | `corpus/llm/a01..a10.txt` | 10 | Producidos por Hermes Agent (glm-5.3-flash vía opencode-go), 10 prompts narrativos distintos | Libre (sin restricciones) |
| IA noticias | `corpus/news/b01..b10.txt` | 10 | Descripciones sintéticas de noticias ES, pipeline SLM del dataset Zenodo (DOI 19449815; paper MDPI *DATA* 11(2):29), RAG/no-RAG × temperaturas 1.0/0.75/0.5 | **CC-BY-4.0** |

Cada pieza está documentada en `corpus/manifest.csv`:
`id, clase, fuente, obra_o_tema, autor_o_modelo, licencia, chars, SHA256`.

## Construcción

- **Humanos**: descarga en `/cache/epub/<id>/pg<id>.txt` de Project Gutenberg
  (User-Agent propio), corte manual desde el 30 % del cuerpo, **sin alterar
  palabras**; fecha de construcción 2026-10-24. Longitud resultante 1,6–5,6 k
  caracteres.
- **IA narrativa**: escritura por el agente con un prompt/tema por pieza;
  correcciones menores de tokens corruptos documentadas en la sesión de trabajo.
- **Noticias**: 30 descripciones por archivo, mezclando buffers A/B y RAG/no-RAG.

## Semillas de compresión

- `corpus/seeds/seed_ia_es.txt` y `seed_hum_es.txt`.
- Se construyen **solo** desde el subconjunto de **TRAIN** (nunca del holdout,
  nunca con material en inglés). En la ronda v2 se retiró el bloque `a07`
  porque pasó al holdout — el test de aislamiento lo verifica.
- Reproducibilidad: los tests comprueban que ningún fragmento de 50 caracteres
  de un texto del holdout aparece en las semillas.

## Split de calibración

- **Unidad de grupo**: autor humano (un grupo por autor; `h14` y `h17` comparten
  Pereda), pieza IA (`a*`), y un único grupo `zenodo` para `b*`.
- **Holdout v2 (fijo, se abre una sola vez)**: `{h08, h16, h19, a05, a07, b03}`.
- **Validación**: leave-one-group-out (LOGO) dentro de TRAIN; el umbral se elige
  solo con TRAIN.
- **v1 histórica** (20 piezas, holdout `{h03,h04,h08,a05,a09}`): conservada en
  `docs/calibration.md` como registro; el método activo es v2.

## Resultado v2 (una apertura)

Umbral 26, margen 8. Holdout: **TP=0, FN=2, FP=0, TN=1, abstención=3**
(`b03`, `h08`, `h19`). Los dos FN son narrativa IA propia; la pieza de noticias
cae en abstención. LOGO-CV en TRAIN: TPR 0.04 / TNR 0.24 → **el índice no
generaliza**; se mantiene como pre-filtro, no como clasificador.

## Reglas de higiene

- Toda pieza nueva requiere: procedencia verificable, licencia escrita, checksum
  y (si es generada) modelo/prompt. Sin licencia clara → fuera del set versionado.
- No se retoca el holdout para mejorar números; una mejora exige un **holdout
  nuevo** declarado antes de ejecutar.
- Los textos crudos de `corpus/human` y `corpus/llm` pueden excluirse del control
  de versiones según licencia; el `manifest.csv` y los documentos siempre se
  versionan.
