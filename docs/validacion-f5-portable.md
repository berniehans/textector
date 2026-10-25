# F5 portable: método y validación reservada

F5 (`f5-portable-v1`) añade un perfil optativo en la versión 0.3.0. F4 sigue
siendo el predeterminado y conserva su significado histórico. El nuevo perfil
es una heurística experimental de estilo, no prueba de autoría ni detector
general de IA.

## Por qué se separó de F4

En los ocho falsos positivos de F4, seis recibían casi 24 puntos por una sola
aparición de «en el fondo»: el normalizador antiguo saturaba con muy poca
evidencia. Los otros dos falsos positivos no contenían clichés detectados y
dependían principalmente de ritmo y compresión. Además, los 300 textos
aplanados de IberAuTexTification quedaban sin índice porque F4 requiere cinco
checks, entre ellos uno que necesita párrafos. El detalle caso por caso y las
contribuciones está en `validation/development-f5/falsos-positivos-f4.json`.

| Fragmentos marcados por F4 | Índice F4 | Cliché/densidad | Otra contribución alta |
|---|---:|---|---|
| `hnew-49836-02` (Unamuno) | 40 | 1 hit, q=1, 24,06 puntos | Compresión 11,11 |
| `hnew-46182-00`, `-01`, `-04` (Valle-Inclán) | 40, 44, 52 | 1 hit por pieza, 24,06 puntos | Dos tenían burstiness≈10,7–11,0 |
| `hnew-39209-05`, `-09` (Juan Ramón Jiménez) | 51, 37 | 1 hit por pieza, 24,06 puntos | Compresión≈11,1 |
| `hnew-13507-05` (Quiroga) | 39 | Sin hits | Burstiness 16,21 + uniformidad 11,68 + compresión 10,74 |
| `hnew-23236-04` (Blasco Ibáñez) | 36 | Sin hits | Burstiness 17,32 + uniformidad 9,02 + compresión 9,87 |

El patrón no se resuelve borrando «en el fondo» del léxico: F5 aumenta el
normalizador de densidad, limita la contribución de una sola coincidencia y
retira del índice las señales de ritmo que confundían prosa humana regular.

## Definición fija del índice

F5 incluye tres checks que operan sobre tokens y no requieren límites de
párrafo:

| Check | Peso | Tratamiento |
|---|---:|---|
| MATTR, ventana de 50 tokens | 0,45 | Transformación de F4, conservada |
| Densidad de clichés | 0,25 | Densidad / 25 unidades ponderadas por 1000 tokens; se multiplica por `min(1, hits/3)` |
| Compresión | 0,30 | Solo aporta evidencia por encima de `q=0,5`; `max(0,(q-0,5)/0,5)` |

El denominador siempre es **1,0**. Si falta MATTR, densidad o compresión, el
índice es `null` y la decisión es abstención. Nunca se redistribuyen los pesos.
Se requieren 50 tokens, 150 bytes limpios y los tres resultados disponibles.
La puntuación no depende de mayúsculas ni de saltos entre párrafos. Burstiness y
uniformidad se calculan como contexto descriptivo y quedan expresamente fuera
del índice; una señal auxiliar insuficiente tampoco impide puntuar F5.

El umbral de desarrollo es 15 con margen 4: se decide humano por debajo de 11,
IA por encima de 19 y se abstiene en la banda inclusiva 11–19. Los pesos y el
margen se fijaron antes de evaluar el conjunto reservado. El umbral se eligió
solo con `validation/external-v1`: máximo de verdaderos positivos de IA entre
los umbrales que logran FP humanos ≤5% y cobertura humana ≥80%; empate resuelto
por el umbral más conservador. Resultó 15. No hay entrenamiento ni pesos
aprendidos.

La calibración de desarrollo contiene 90 fragmentos humanos pre-2020, 200
cuentos TinyStories y 300 textos IA literarios de IberAuTexTification. A umbral
15, detectó 177/200 TinyStories (88,5%), 41/300 Iber (13,7%) y produjo 2/90
falsos positivos humanos (2,2%); decidió sobre 73/90 humanos (81,1%). La gran
diferencia entre corpus ya mostraba que el perfil no es un detector general.
Los resultados completos y la lista de scores están en
`validation/development-f5/calibration.json`.

## Conjunto reservado

Antes de escribir F5 o calibrar el umbral se fijaron 536 textos, sus hashes, las
fuentes y criterios de promoción en `validation/reserved-f5-v1/selection-lock.json`
y `manifest.jsonl`. El SHA-256 del manifiesto es
`b7d7de3896345dbb1f53d0ee7c49da88e1b6c6b74ac51f08b97d311c8404bce8`.
Los snapshots de los seis libros humanos están fechados en 2018 y representan
cuatro autores no incluidos en el desarrollo: Concha Espina, Armando Palacio
Valdés, Rafael Delgado y Felipe Trigo. Hay 96 fragmentos humanos (16 por libro).

Los 200 cuentos IA proceden de otro shard, `stories_02.json`, de TinyStories en
español, que el autor describe como generado con Gemini 1.5 Flash. Se separó de
desarrollo por shard y prompt. Los 240 textos Iber son 40 por cada uno de seis
códigos de generador, con identificadores/prompt nuevos. No se solicitó al
modelo ninguna generación nueva.

Las versiones fuente están fijadas a commits: [TinyStories en español, su
idioma y licencia Apache 2.0](https://huggingface.co/datasets/robrenaud/multilingual_tinystories),
[el autor documenta que generó el corpus español con Gemini 1.5 Flash](https://huggingface.co/datasets/roneneldan/TinyStories/discussions/7),
[IberAuTexTification: idiomas, tarea, modelos y licencia CC BY-NC-ND 4.0](https://huggingface.co/datasets/Genaios/iberautextification), y
[GITenberg, libros de Project Gutenberg en repositorios versionados](https://gitenberg.github.io/).
Los URLs, commits, fechas y hashes exactos de cada recurso figuran en
`validation/reserved-f5-v1/sources.json` y el manifiesto. Los textos IA de
licencia CC BY-NC-ND no se distribuyen en el repositorio: se pueden restaurar
localmente con `python -B tools/fetch_reserved_corpus.py` y verificar contra
los SHA-256 del manifiesto.

La candidatura F5, sus pesos, umbral, código y hashes se guardaron en
`candidate-lock.json` **antes de abrir las puntuaciones reservadas**. La
evaluación compara cada pieza con el F4 original preservado en
`validation/baselines/f4`. El resultado se registra en `results.json`; el
conjunto quedó consumido y no se recalibró sobre él.

### Criterios fijados antes de puntuar

Se considera promoción solo si se cumplen todos: FP humanos sobre los 96 ≤5%,
cobertura de decisión humana ≥80%, detección TinyStories sobre sus 200 casos
≥80% y cobertura de score Iber ≥90%. Si falla cualquiera, el perfil queda sin
promover y se informa la métrica fallida; no se ajusta contra este reservado.

## Comparación congelada F4 / F5

Se puntuaron una sola vez los 536 textos después de congelar F5. F4 se ejecutó
desde el snapshot anterior a la modificación; F5 usó umbral 15/margen 4. Las
abstenciones separan banda e insuficiencia. `FN` cuenta solo los textos IA
clasificados como humanos; las abstenciones no se esconden dentro del FN.

| Panel | N | F4: TP / FP / FN / abst. | F5: TP / FP / FN / abst. | Score F5 | Decisión F5 |
|---|---:|---:|---:|---:|---:|
| Humanos pre-2020, autores nuevos | 96 | 0 / 5 / — / 38 | 0 / **0** / — / 3 | 96/96 (100%) | 93/96 (96,9%) |
| TinyStories, shard nuevo | 200 | 185 / 0 / 1 / 14 | 183 / 0 / 2 / 15 | 198/200 (99%) | 185/200 (92,5%) |
| Iber, prompts nuevos | 240 | 0 / 0 / 0 / **240** | 38 / 0 / 120 / 82 | 227/240 (94,6%) | 158/240 (65,8%) |

Los cinco falsos positivos F4 de los nuevos libros desaparecen con F5; el perfil
no generó FP en 96 humanos y se abstuvo en tres, todos por banda. En TinyStories
F5 detectó 183/200 (91,5%), dos puntos porcentuales menos que F4, y se abstuvo
en 15. En Iber, F4 no produjo ningún score; F5 lo produjo para 227/240, pero
solo clasificó como IA 38/240 (15,8%). La cobertura de score no equivale a
capacidad de detección: en este panel la sensibilidad condicionada a decisión
es 24,1%, con 120 clasificados como humanos y 82 abstenciones.

Sobre el panel completo, F5 obtuvo 221/440 verdaderos positivos IA (50,2%),
122 FN, cero FP entre humanos y 100/536 abstenciones (85 por banda y 15 por
insuficiencia). La cobertura de decisión fue 81,3%; F4 obtuvo 185/440 TP
(42,0%), cinco FP y 292 abstenciones. Las cuatro cotas fijadas se cumplieron,
por eso F5 queda **promovido a perfil optativo experimental**. Los resultados
no prueban generalización: el panel Iber revela baja detección y los proveedores
se repiten entre desarrollo y reservado. La tabla completa y el detalle por
pieza están en `validation/reserved-f5-v1/results.json`.

### Limitaciones

Los humanos son literatura histórica y las generaciones incluyen cuentos
infantiles y prosa literaria; permanecen diferencias de época, género, autor y
longitud. Los 96 extractos pertenecen a seis libros, pero solo cuatro autores,
así que no son 96 observaciones independientes. Los proveedores de IA se
repiten entre desarrollo y reservado, aunque cambian los shards, prompts y
textos; la prueba no demuestra transferencia a proveedores desconocidos. La
etiqueta y los resultados son evidencia comparativa de corpus, no certeza sobre
la autoría de un texto individual.
