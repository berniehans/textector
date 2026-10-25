# Auditoría de búsqueda de corpus confirmatorio para F5

**Fecha de consulta:** 25 de octubre de 2026

**Pregunta:** ¿hay una fuente pública, nueva, licenciada y suficientemente trazable de narrativa española generada por IA que permita una confirmación independiente de F5?

**Alcance:** revisión de fichas oficiales, tarjetas de datos, repositorios de los autores y páginas institucionales. No se puntuaron textos ni se abrió ningún conjunto reservado.

## Criterios de admisión fijados

Una fuente IA solo pasa a preparación confirmatoria si satisface todos estos puntos:

1. Textos narrativos completos en español, no preguntas/respuestas, tramas, sinopsis, noticias o textos traducidos.
2. Procedencia y generador identificables, con versión/checkpoint o identificación suficiente para declarar el alcance.
3. Unidades independientes suficientes por generador: como objetivo de planificación, 150 prompts/documentos; agrupar reintentos, paráfrasis y múltiples salidas del mismo prompt.
4. Licencia o permiso que permita el uso de investigación y la conservación local de los textos, o un procedimiento verificable de acceso legítimo.
5. Separación respecto de todo material ya usado en desarrollo, selección de señal, F5, F4, cribados previos y bancos de prompts.

Una ficha pública o una licencia declarada no demuestra por sí sola que las llamadas de generación se hayan ejecutado como se describe. La procedencia del proveedor se consignará como declarada por los publicadores, salvo evidencia independiente adicional.

## Fuentes IA evaluadas

| Fuente | Evidencia pública consultada | Resultado para confirmación F5 narrativa |
|---|---|---|
| IberAuTexTification | Corpus de detección/atribución en idiomas ibéricos; ya fue usado en calibración y evaluación externa del proyecto. | **Excluir:** exposición previa; no cuenta como fuente nueva. |
| TinyStories español / Gemini 1.5 Flash | Relatos infantiles; un shard ya se usó en desarrollo y otro en evaluación externa reservada. | **Excluir:** shards distintos no eliminan exposición al corpus, prompt ni familia de generación ya evaluados. |
| Story Writing Benchmark | La comparación local documentada deja, tras excluir prompts vistos, 448 filas en siete checkpoints, 32 prompts por checkpoint y solo continuaciones de escena. | **Solo estrés exploratorio:** mismo benchmark y formatos estrechos; no constituye replicación independiente. |
| StereoTales | La ficha declara 2.844 muestras españolas y 65.412 salidas de historias cortas en español, con escenarios y plantillas traducidos/revisados. | **Excluir de confirmación:** ya usado como estrés en el proyecto; no reetiquetar como fuente nueva. |
| WildChat (AllenAI; preflight de ficción española) | Snapshot `475fa490b5e28692362af7a6ec66810caf4a9847`, licencia ODC-BY; se escanearon localmente 529.512 filas de seis shards. La tabulación local idioma×modelo encontró 11.364 filas `gpt-3.5-turbo` en español, 1.142 `gpt-4` y 2 `gpt-4-1106-preview`. Un filtro estricto dejó 104, 27 y 0 prompts únicos, respectivamente. | **Excluir de confirmación:** cada generador queda bajo el mínimo acordado de 150 prompts; no se combinan modelos. Se exigió conversación de un solo intercambio, dos turnos en español, sin banderas de redacción/toxicidad, sin patrones de PII o solicitud personal/de mundo real ni contenido sensible, y respuesta de ≥50 tokens con ≥3 oraciones; se deduplicaron prompts normalizados. El resumen y sus huellas están en `validation/narrative-v2-corpus-audit/wildchat-spanish-fiction-preflight.json`; no se escribieron prompts, respuestas ni IDs sin hash. Los shards temporales se borraron tras su lectura. El filtro fue heurístico y no certifica ausencia de todo dato sensible, por lo que no se puntuó F5. |
| ROBOT-TALK (búsqueda ampliada) | 3.123 textos comparables en español de humanos y seis modelos; incluye Gemini, Claude, GPT-3.5/4, Mixtral y DeepSeek. | **Excluir de esta pregunta:** la ficha oficial limita los géneros a noticias, reseñas de cine y artículos científicos de lingüística; no es narrativa literaria. [Ficha UCM](https://www.ucm.es/robottalk/corpus-robot-talk). |
| Unified TELL (búsqueda ampliada) | Agregación de 9,179,122 filas, con 52,191 en español y varias fuentes de detección. | **Excluir de confirmación narrativa nueva:** la ficha identifica `symanto/autextification2023` como fuente incluida, material ya usado en IberAuTexTification, y el agregado mezcla datasets/licencias; no se identificó una partición nueva, independiente y narrativa. [Ficha del agregado](https://huggingface.co/datasets/suraj-ranganath/unified_tell_dataset). |
| Estudios de microficción española | “Can Artificial Intelligence Write Like Borges?” reporta seis microficciones humanas y seis IA en su comparación principal; la IA son tres relatos de ChatGPT-3.5 y tres de Monterroso. | **Insuficiente:** seis ejemplos por sistema están muy por debajo de 150 por generador. El estudio aporta un posible banco exploratorio, no una confirmación. [Artículo y materiales](https://doi.org/10.3390/app15126802). |
| Relatos de sesgo social generados por GPT-4 | Un estudio reporta 100 relatos ficticios en español de aproximadamente 150 palabras, generados con ChatGPT-4. | **No elegible:** 100 queda bajo el mínimo 150 y el artículo indica que los datos se entregan bajo solicitud al autor, no como corpus descargable público. [Artículo](https://www.mdpi.com/2076-0760/14/3/170). |
| IberoTales español | La tarjeta declara 2.283 registros, licencia Apache-2.0, idioma español y generación con `cohere-r-plus`; los campos incluyen `trama`, pregunta y respuesta. La tarjeta define `trama` como resumen/esquema y avisa que el conjunto sigue en desarrollo activo. | **No elegible como narrativa completa:** es un recurso nuevo y rastreable para resúmenes de trama, pero el contenido narrativo central no son cuentos completos. No usarlo como sustituto del dominio literario. Como máximo, panel exploratorio separado si una pregunta posterior incluye sinopsis. |
| Narrative Similarity Task | La documentación describe más de 1.000 triples de resúmenes de historias de Wikipedia y 1.900 triples sintéticos para entrenamiento. | **No elegible:** unidades son resúmenes/triples para similitud, no relatos completos en español; no usar train/test etiquetados como una fuente de generación narrativa independiente. |
| Corpus sintético español de noticias (Mistral 7B Instruct) | Zenodo anuncia 18.236 descripciones sintéticas en español, con versiones RAG/NO-RAG, temperaturas y titulares de dos periódicos. | **No elegible para narrativa:** noticias/descripciones, no ficción narrativa; género y contenido fuente son distintos. Puede servir como prueba separada de transferencia periodística. |
| Synthetic-Dataset-Childrens-Stories (ContextReq) | Tarjeta declara relatos sintéticos, MiniCPM5-1B-GGUF, 30.000 textos y CC BY-NC 4.0; el idioma de la colección consultada no es español. | **No elegible:** idioma incorrecto y dominio infantil; no convertir ni traducir para crear una fuente confirmatoria. |
| StoryScope | Documentación declara 10.272 prompts de cuentos de antologías Books3 y cinco generadores, pero el material consultado es inglés; no incluye el texto humano original por copyright. | **No elegible:** idioma distinto y fuente Books3; tampoco se confirmó que el repositorio tenga datos en español. |
| ROBOT-TALK como posible futuro candidato | La ficha institucional sí informa cantidades por género y generador, pero su población son textos periodísticos, reseñas y artículos especializados. | **Reevaluar solo si cambia el mandato** a una prueba de transferencia entre géneros y se documentan los términos de acceso. No mezclar con el análisis literario principal. |

## Candidatos humanos para preparar en paralelo

Las fuentes históricas son adecuadas para ampliar autores y obras; la admisión de cada obra aún requiere versión fijada, fecha de publicación comprobable, licencia, deduplicación a nivel de texto y cruce de autor/título contra todas las exposiciones históricas conocidas.

- **CoNSSA:** su repositorio oficial describe novelas españolas publicadas entre 1880 y 1939; 217 textos están disponibles como texto/TEI. Los textos publicados se declaran de dominio público y metadatos/marcado CC BY. Es un candidato prioritario para narrativa pre-2020.
- **ELTeC-spa:** el repositorio oficial declara novelas españolas del período 1840–1920 y dominio público para textos; la edición v0.9.1 publicada en 2021 contiene 84 novelas. Usar una versión fijada, no mezclar automáticamente la rama mutable `master` con la edición publicada.
- **Spanish-PD-Books:** la ficha declara 302.640 textos y 13,9 mil millones de palabras provenientes de bibliotecas/Internet Archive, dominio público y OCR automático. Es una reserva amplia, pero no está filtrada a narrativa ni limpia de OCR; primero hay que seleccionar metadatos/obras elegibles y hacer QC.
- **ONE71:** contiene 11 novelas de 11 autores con licencia CC BY 4.0, pero la ficha indica que la descarga pública está codificada/scrambled. No es una ruta directa al corpus de prosa utilizable para esta confirmación.

No se declara todavía una cifra final de autores nuevos: los conteos brutos de catálogos no sustituyen el cruce completo de identidad, seudónimos, coautorías y títulos contra `corpus/manifest.csv`, los manifiestos no reservados de desarrollo y la documentación no reservada de exposiciones anteriores. Las obras reservadas no se abren ni se usan para muestreo.

## Decisión y puerta de continuación

**Estado: no-go para puntuar confirmación F5 con las fuentes públicas examinadas.** Ninguna fuente nueva pasó simultáneamente narrativa completa en español, trazabilidad, independencia, tamaño y derechos. WildChat dejó 104 prompts únicos de `gpt-3.5-turbo`, 27 de `gpt-4` y 0 de `gpt-4-1106-preview`, frente al mínimo fijado de 150 por generador. No se combinan modelos, no se cuentan sinopsis como relatos y no se usa F5 para clasificar o seleccionar ejemplos.

**Cierre de esta ronda:** no se creó un lock confirmatorio ni se puntuaron textos nuevos. El cruce humano disponible es preliminar: las 210 identidades son candidatas brutas, no 210 autores validados; las licencias, los títulos, las traducciones y los alias deben resolverse antes de fijar una muestra. WildChat no supera el tamaño por generador y su filtro automatizado tampoco certifica privacidad completa. Bajo las puertas acordadas, avanzar a puntuación o relajar el mínimo sería metodológicamente inválido. El resultado de la ronda es **sin corpus independiente suficiente; F5 sigue experimental y permanece sin cambios el umbral 15/margen 4**.

La preparación puede avanzar sin puntuar F5:

1. Congelar el registro de exposiciones previas usando solo documentación y archivos no reservados.
2. Congelar snapshots/licencias de CoNSSA, ELTeC-spa y Spanish-PD-Books y construir el cruce de autor/título.
3. Extraer solo metadatos primero de la fuente humana grande; seleccionar narrativa y obras pre-2020 antes de leer o puntuar pasajes.
4. Mantener WildChat excluido: el preflight fijado no llegó a 150 prompts por modelo y el filtro no garantiza retirar toda información sensible. No exportar sus textos.
5. Mantener un registro de candidatos IA con `incluido`, `excluido` y motivo, junto con commit, licencia, modelo, prompts y unidad independiente.
6. No ejecutar el scorer ni estimar resultados confirmatorios hasta encontrar una fuente IA que pase las cinco condiciones y el tamaño por generador.

Si la búsqueda adicional no encuentra esa fuente, cerrar la fase con resultado **sin corpus independiente suficiente; F5 permanece experimental, sin cambio de 15/4**. No se extrapolan resultados del cribado ni se generan textos nuevos dentro de este plan.

## Fuentes consultadas

- [ROBOT-TALK, Universidad Complutense de Madrid](https://www.ucm.es/robottalk/corpus-robot-talk)
- [Tarjeta IberoTales español, Hugging Face](https://huggingface.co/datasets/somosnlp-hackathon-2025/ibero-tales-es)
- [Datos de Narrative Similarity Task](https://narrative-similarity-task.github.io/data/)
- [Corpus sintético de noticias españolas, Zenodo](https://zenodo.org/records/17951564)
- [StereoTales, tarjeta Hugging Face](https://huggingface.co/datasets/giskardai/StereoTales)
- [Story Writing Benchmark, tarjeta Hugging Face](https://huggingface.co/datasets/lars1234/story_writing_benchmark)
- [WildChat, tarjeta oficial de AllenAI en Hugging Face](https://huggingface.co/datasets/allenai/WildChat)
- [Estadísticas agregadas de WildChat en el visor de conjuntos de Hugging Face](https://datasets-server.huggingface.co/statistics?dataset=allenai/WildChat&config=default&split=train)
- [AI Fiction in the Wild, proyecto de investigación basado en WildChat](https://ai-fiction-wild.com/)
- [Subconjunto inglés y metodología de etiquetado de AI Fiction in the Wild](https://ai-fiction-wild.com/about)
- [Herramienta de preflight de WildChat](../tools/preflight_wildchat_spanish_fiction.py) y [resumen de metadatos y huellas](../validation/narrative-v2-corpus-audit/wildchat-spanish-fiction-preflight.json)
- [ROBOT-TALK, ficha oficial UCM](https://www.ucm.es/robottalk/corpus-robot-talk)
- [Unified TELL, ficha de Hugging Face](https://huggingface.co/datasets/suraj-ranganath/unified_tell_dataset)
- [Microficción española: “Can Artificial Intelligence Write Like Borges?”](https://doi.org/10.3390/app15126802)
- [Relatos ficticios de GPT-4 para análisis de sesgo social](https://www.mdpi.com/2076-0760/14/3/170)
- [CoNSSA, repositorio oficial](https://github.com/cligs/conssa)
- [ELTeC-spa, repositorio oficial](https://github.com/COST-ELTeC/ELTeC-spa)
- [Spanish-PD-Books, tarjeta Hugging Face](https://huggingface.co/datasets/PleIAs/Spanish-PD-Books)
- [ONE71, ficha de Språkbanken](https://spraakbanken.gu.se/en/resources/one71)
