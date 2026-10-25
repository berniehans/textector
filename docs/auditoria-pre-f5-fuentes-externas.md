# Auditoría de solapamiento antes de puntuar F5

**Fecha:** 25 de octubre de 2026

**Propósito:** comprobar identidad de modelos, independencia de prompts y solapamiento bibliográfico antes de usar fuentes candidatas.

**Límite:** esta auditoría no puntuó ningún texto con F5 y no modificó señales, umbral ni margen.

## Resultado del benchmark de relatos de IA

Se comparó `work/corpus-scout/average.csv` (benchmark `story_writing_benchmark`) con los manifiestos de **desarrollo** de `validation/narrative-v1`. Se usaron los identificadores de modelo y `prompt_id`; los cálculos no incluyen datos reservados.

- El archivo local tiene 8.520 filas; 3.360 están etiquetadas en español, repartidas en 15 modelos, con 224 filas por modelo.
- Los manifiestos de desarrollo contienen ocho checkpoints y 276 `prompt_id` distintos.
- Los ocho checkpoints de desarrollo están presentes en el benchmark y sus 52 prompts españoles por modelo ya aparecen en desarrollo. No aportan filas nuevas para esta comparación.
- Los otros siete checkpoints son `SuperNova-Medius`, `C4AI Command R`, `Aya Expanse 32B`, `Aya Expanse 8B`, `Qwen 2.5 14B`, `Aya 23 8B` y `Phi-4`.
- Cada uno tiene 224 filas españolas en el archivo bruto. Para cada checkpoint, 20 de sus 52 prompts coinciden con prompts de desarrollo. Al excluir esos prompts completos quedan **64 filas por checkpoint**, procedentes de **32 prompts nuevos**.
- En total quedan **448 relatos** de IA (7 × 64), con 32 prompts nuevos por checkpoint. Esos prompts nuevos no están emparejados entre los siete checkpoints.
- Las 448 filas restantes son todas `scene_continuation`; no quedan relatos completos ni comienzos de escena en ese subconjunto limpio.

**Lectura:** hay un subconjunto útil para un estrés exploratorio por checkpoint y por continuación de escena, condicionado al mismo benchmark. No es una réplica independiente de fuente, y su cobertura de formatos es estrecha. Con 32 prompts por checkpoint no lo tomaría como confirmación de la puerta de detección por fuente.

## Comparación bibliográfica de ONE71

Se compararon los metadatos de los 11 autores y títulos de ONE71 con la unión de `corpus/manifest.csv` y `validation/narrative-v1/development/manifest-human.jsonl`: 32 autores y 32 títulos humanos únicos ya usados.

- Coincidencias normalizadas de título: **0/11**.
- Coincidencias de autor tras normalizar mayúsculas, tildes y puntuación: **0/11**.
- Todos los títulos de ONE71 son novelas españolas de primera edición publicadas entre 1951 y 1971; el registro de Språkbanken declara CC BY 4.0 y ofrece descarga.

La independencia bibliográfica a nivel de autor y título es favorable. Sin embargo, son solo **11 autores**; muchos fragmentos extraídos de las mismas novelas no aumentan el número de unidades independientes para evaluar falsos positivos agrupados por autor. No basta para certificar el límite humano acordado. Además, no se descargaron ni se compararon huellas de los textos completos: el resultado de solapamiento aquí es bibliográfico, no una deduplicación textual.

## Spanish-PD-Books de PleIAs

Es demasiado grande para usarlo directamente sin preparación y la colección incluye monografías que no necesariamente son narrativa. No hay una tabla local de metadatos seleccionados para cruzar títulos/autores con los libros de desarrollo, y no se descargaron los 35,7 GB. Por tanto, esta auditoría no puede declarar cero solapamiento para esa fuente. Antes de reservar cualquier obra hay que obtener metadatos, filtrar narrativa publicada antes de 2020, cruzar autor/título y deduplicar por huellas normalizadas contra los textos de desarrollo.

## Decisión de preparación

1. **No puntuar F5 aún** con estos candidatos.
2. ONE71 puede pasar a una etapa de preparación y control de calidad como conjunto humano complementario, con la limitación explícita de 11 autores.
3. El subconjunto de siete modelos del benchmark puede quedar como estrés exploratorio si se conserva la exclusión de prompts vistos; no debe presentarse como evidencia independiente ni como cobertura general de narrativa.
4. Para una confirmación real, conseguir una fuente humana con más autores y una fuente de IA que no sea el benchmark ya usado; hacer deduplicación textual antes de bloquear y puntuar.

## Reproducibilidad

Comparación calculada a partir de:

- `work/corpus-scout/average.csv`
- `work/textector/corpus/manifest.csv`
- `work/textector/validation/narrative-v1/development/manifest-ai.jsonl`
- `work/textector/validation/narrative-v1/development/manifest-human.jsonl`

La revisión de ONE71 se contrastó con su ficha y catálogo público: https://spraakbanken.gu.se/en/resources/one71. Ningún dato reservado formó parte de estos conteos.
