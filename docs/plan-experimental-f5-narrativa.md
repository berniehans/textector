# Plan experimental de F5 para narración en español

## Propósito y estado

Este documento convierte la revisión independiente con SOL 6.1 en un protocolo de investigación para mejorar F5 como **prefiltro de prosa narrativa en español**. No autoriza promover una variante ni cambia la versión vigente. `f5-portable-v1` permanece congelado como control; durante la fase diagnóstica se conservan el umbral **15**, el margen **4** y los pesos actuales (MATTR 0,45; clichés 0,25; compresión positiva 0,30).

Las puertas acordadas siguen siendo: falsos positivos humanos ≤5%, cobertura de decisión humana ≥80% y detección IA ≥80% por checkpoint/fuente. Este protocolo distingue el cumplimiento observado en una muestra de la evidencia estadística necesaria para sostener que se cumplen esas puertas.

### Decisiones de protocolo acordadas

- La puerta de promoción requiere tanto estimaciones puntuales que pasen los límites como límites unilaterales del 95% que los sostengan.
- Una señal solo se describe como una mejora práctica frente a B0 si aumenta la detección al menos **5 puntos porcentuales**; se informan también sus cambios en FP y cobertura.
- M100 usa ventana 100 con textos de al menos 100 tokens y **fallback a MATTR50** para 50–99 tokens. Menos de 50 tokens conserva la abstención actual. El perfil se denomina `M100-fallback50`.
- El banco C2-v2 tiene al menos **ocho documentos independientes por clase**, bloques IA/humano emparejados en bytes y agregación mediana. Las longitudes se fijan usando solo metadatos y disponibilidad de desarrollo, antes de puntuar.
- Las variantes confirmatorias usan datos nuevos y fuentes/checkpoints no usados para seleccionar señales. Las cifras de desarrollo, incluso con intervalos, no certifican promoción.

### Hipótesis

El estimando principal para cada perfil es el vector formado por FP humano sobre todos los humanos elegibles, cobertura de decisión humana y detección IA sobre todos los casos elegibles de cada checkpoint/fuente. Las abstenciones permanecen en los denominadores de FP y detección; se desglosan por causa.

- **H0 global:** el perfil incumple al menos una puerta de promoción en la población objetivo.
- **H1 global:** el perfil cumple simultáneamente FP humano ≤5%, cobertura humana ≥80% y detección IA ≥80% en cada checkpoint/fuente declarada, con los límites unilaterales del 95% del lado requerido.
- Para cada factor L2, C2-v2 y M100-fallback50, **H0 de mejora:** no aumenta la detección frente a B0 al menos cinco puntos porcentuales en cada fuente; **H1 de mejora:** el aumento es ≥5 puntos en cada fuente. Esos contrastes son exploratorios en desarrollo.
- Para las interacciones del factorial, **H0:** los efectos de los factores son aditivos en la escala de proporciones; **H1:** existe al menos una interacción. Una interacción no se interpreta como beneficiosa sin revisar sus efectos por fuente y las puertas humanas.

Estas hipótesis describen decisiones del prefiltro en una población definida; no afirman ni prueban autoría individual.

## Evidencia disponible y sus límites

La comparación de desarrollo existente sobre 1.912 textos (1.792 IA y 120 humanos) encontró:

| Variante | Detección IA | FP humanos | Cobertura humana |
|---|---:|---:|---:|
| F5 actual (B0) | 2,01% | 0/120 (0%) | 92,50% |
| F4 de referencia | 63,73% | 11/120 (9,17%) | 91,67% |
| L2: escala de densidad de clichés 2,5, conserva requisito de 3 hits | 13,78% | 3/120 (2,50%) | 88,33% |
| C2 histórico: semillas de igual prefijo/longitud | 2,68% | 0/120 (0%) | 91,67% |

En el panel de 157 casos IA revisados manualmente como español, B0 detectó 1,27%, L2 15,29% y F4 63,06%. El C2 histórico cambia contenido además de longitud y no identifica el efecto causal de igualar longitud. Los 1.388 casos aún no confirmados como español siguen etiquetados **español provisional**. Estas cifras sirven para diagnóstico; no son una confirmación independiente.

## Fase 0: protocolo, datos y control congelados

Antes de puntuar una nueva variante:

1. Congelar hashes de código, perfil, léxico, semillas, manifiestos, textos y reglas de preprocesamiento.
2. Reproducir B0 y F4 sobre los mismos casos elegibles y comprobar que B0 coincide con la salida vigente.
3. Preservar los resultados históricos sin sobrescribirlos. Los nuevos perfiles y resultados reciben identificadores nuevos.
4. Mantener fuera de esta exploración cualquier conjunto reservado. No abrir sus textos, scores ni resultados para elegir señales, parámetros, semillas o reglas.
5. Fijar etiquetas y exclusiones sin consultar scores. Registrar idioma (`español`, `mixto`, `otro`, `incierto`), fuente, checkpoint, familia base, prompt, autor, obra/documento, género y longitud.
6. Mantener como paneles distintos: español verificado, mixto, otro idioma y español provisional. Los casos provisionales no cuentan como español confirmado.

La inclusión principal requiere procedencia verificable y español confirmado. Se documentan por separado las abstenciones por insuficiencia de texto y las abstenciones por banda de decisión. Se publican también el número y la proporción excluidos o insuficientes; el rendimiento no se describe como aplicable a textos cortos si estos no son elegibles.

## Fase 1: auditoría lingüística y de procedencia

Los 157 textos IA en español verificados son un panel de diagnóstico. No se extrapola sin ponderación desde la muestra estratificada de 160 a todos los 1.548 negativos del heurístico. Los 1.388 restantes permanecen provisionales hasta su verificación.

Se prioriza:

- Verificar idioma y procedencia de todos los casos que se propongan para la futura confirmación.
- Auditar una muestra estratificada adicional del desarrollo para estimar contaminación, conservando las probabilidades de selección y ponderando los resultados si se calcula una tasa poblacional.
- Aplicar reglas previas para texto mixto, traducciones, OCR defectuoso y material humano asistido.
- No decidir qué revisar, excluir o reclasificar según el score o la predicción de F5.

Si una fuente no permite verificar idioma o procedencia, se conserva como exploratoria y no cuenta para aprobar las puertas. Si el muestreo encuentra errores concentrados en una fuente o checkpoint, se revisa esa celda antes de generalizar.

## Fase 2: diagnósticos de señales

Cada señal se evalúa primero de forma aislada, manteniendo las demás y el umbral/margen congelados. Además de predicciones, se guardan distribuciones de scores, contribuciones, abstenciones e insuficiencias por longitud, género, autor, prompt, checkpoint y fuente.

### Clichés (`L2`)

Validar la variante ya especificada: escala máxima de densidad ponderada 2,5 en vez de 25, con el léxico, pesos y factor de evidencia actual (hasta tres hits) sin cambios. Registrar qué IDs de patrón contribuyen, sus frecuencias y la distribución humano/IA, sin incluir fragmentos crudos en reportes.

Si los falsos positivos se concentran en pocas entradas, cualquier léxico alternativo se congela como una variante nueva y se vuelve a evaluar en datos no usados para seleccionar esas entradas. No se borran clichés retrospectivamente del mismo conjunto que confirmó el problema.

### Compresión (`C2-v2`)

El C2 histórico permanece solo como antecedente. El nuevo experimento usa un banco de ejemplares independiente de evaluación y de sus derivados:

- Varios documentos humanos e IA por fuente, equilibrados por género y tema cuando sea posible.
- Pares de longitud igual medida **después de la normalización**, con varios bloques por documento y regla determinista de selección.
- Comparaciones dentro del mismo ejemplar al variar longitud, además de comparaciones entre ejemplares, para separar longitud de contenido.
- Agregación fijada antes de ver resultados (mediana de deltas entre bloques) y publicación de la dispersión y sensibilidad a cada ejemplar.
- Separación de semillas, documentos de evaluación, prompts, obras y fragmentos relacionados.

Se informa el desempeño de cada bloque y de la agregación. Si el resultado depende de un bloque, una fuente o un tema, la señal se considera frágil. Que C0 y B0 tengan las mismas decisiones solo significa que en esos casos la contribución actual no cambió las decisiones; no prueba que compresión no aporte información ni que no afecte scores o abstenciones.

### MATTR (`M100`)

MATTR actual usa ventana de 50 tokens, paso de 1 token y normalización fija. La única alternativa exploratoria predefinida es ventana de 100 tokens, con el resto de la transformación sin cambios. Así se limita la búsqueda y se mide explícitamente el coste de insuficiencia para textos entre 50 y 99 tokens. No se ajustan a la vez los puntos 0,55/0,85 de normalización.

Si el cambio de ventana altera fuertemente la cobertura por longitud o género, se reporta como dependencia del dominio. No se presentan ventanas adicionales elegidas después de observar resultados como confirmación.

## Fase 3: matriz factorial acotada

Tras los diagnósticos aislados, se compara un diseño de hasta ocho perfiles (2 × 2 × 2), para poder medir interacciones sin búsqueda abierta:

| Factor | Nivel actual | Nivel alternativo |
|---|---|---|
| Clichés | escala 25 | L2, escala 2,5 |
| Compresión | semillas actuales congeladas | C2-v2, banco balanceado y agregación predefinida |
| MATTR | ventana 50 | M100, ventana 100 |

Se incluyen las ocho combinaciones posibles, identificadas con nombres y hashes propios, además de B0 y F4 como referencias. Pesos, umbral y margen permanecen congelados en esta fase; no se redistribuyen pesos automáticamente cuando cambie una señal. Si una combinación elimina una señal o cambia su peso, se cuenta como un factor adicional y exige un protocolo revisado antes de puntuar.

Los resultados de toda la matriz se conservan, no solo el perfil ganador. Se comparan cambios frente a B0 por caso y por grupos; se examinan interacciones y regresiones por fuente, género y longitud.

## Particiones y prevención de filtraciones

Las particiones se hacen por grupos relacionados, nunca por fragmento aleatorio:

- Humanos: mantener una obra completa y sus fragmentos en una sola partición; separar autores entre desarrollo y confirmación.
- IA: mantener juntos prompt, documento de origen y versiones/paráfrasis relacionadas; medir explícitamente generalización a prompts reservados.
- Semillas de compresión: ningún documento, fragmento ni derivado del banco de semillas puede aparecer en evaluación.
- Datos: registrar relaciones de linaje entre modelos; reportar checkpoint y familia base para no contar modelos derivados como fuentes independientes.

Los hashes son necesarios para reproducir el corpus, pero no sustituyen esta separación por linaje. Se distinguen la semilla de muestreo, las semillas textuales de compresión y la semilla de cualquier generación del dataset.

## Métricas y criterio estadístico

Los denominadores se fijan antes de evaluar:

- **FP humano** = textos humanos clasificados como IA / todos los textos humanos elegibles. Las abstenciones permanecen en el denominador y no son FP.
- **Cobertura humana** = textos humanos con decisión (IA o humano) / todos los humanos elegibles.
- **Detección IA** = textos IA clasificados como IA / todos los IA elegibles de ese checkpoint/fuente. Las abstenciones permanecen en el denominador y no son detecciones.
- **FP condicionado a decisión** se reporta como métrica secundaria, nunca sustituye FP sobre todos los humanos.
- Abstención por banda, insuficiencia, resultados por longitud y proporción excluida se reportan por separado.

Se reportan estimaciones puntuales y límites unilaterales del 95% ajustados por agrupación (autor/obra para humanos; prompt/documento para IA), junto con denominadores y número de grupos. Una sensibilidad binomial por filas puede añadirse, pero no sustituye el análisis agrupado. El plan de tamaño muestral se hace por checkpoint/fuente y cantidad de grupos independientes, no solo por cantidad de fragmentos.

**Regla acordada para afirmar cumplimiento:** la estimación puntual debe satisfacer la puerta y, además, el límite unilateral correspondiente debe sostenerla (límite superior de FP ≤5%; límites inferiores de cobertura humana y detección IA ≥80%). Si no hay grupos o casos suficientes para estimar esos límites con estabilidad, la conclusión es **datos insuficientes**, aunque el porcentaje observado cruce la puerta.

## Regla de parada por futilidad

Tras la matriz factorial y antes de gastar datos confirmatorios, evaluar si alguna variante se acerca de forma reproducible a las tres puertas. L2 parte de 13,78% de detección IA y C2 histórico de 2,68%; C1 raw mostró 33,33% de FP humano. Si ninguna variante mejora de forma consistente y con holgura el desempeño por fuente, o si las mejoras dependen de una celda aislada mientras otra falla claramente, detener esta familia de señales y documentar **no viable para promoción con esta configuración**.

No se amplía la búsqueda de parámetros indefinidamente ni se usa la confirmación para rescatar un resultado negativo. Una nueva familia de señales requiere hipótesis, variantes y presupuesto de evaluación preespecificados.

## Fase 4: selección, calibración y confirmación independiente

1. Seleccionar como máximo una candidata con desarrollo y registrar por qué se eligió; no usar la confirmación para elegir entre candidatas.
2. Mientras el mandato vigente conserve 15/4, la candidata se confirma con esos valores congelados.
3. Si posteriormente se autoriza calibrar umbral o margen, hacerlo solo en desarrollo, congelar el perfil completo y obtener una **confirmación independiente nueva**. Una confirmación ya consultada no sirve para validar cambios posteriores.
4. La confirmación incluye textos humanos narrativos en español publicados antes de 2020, diversidad de autores y géneros, y ejemplos IA públicos con fuente y checkpoint verificables. Todo caso confirmatorio tiene idioma y procedencia comprobados antes de puntuar.
5. Evaluar por checkpoint/fuente y familia base, además del total; ninguna media agregada puede ocultar una fuente que falle.

La salida final puede ser: promover una variante si cumple todas las puertas; mantener F5 experimental si no; limitar explícitamente el ámbito si la evidencia solo cubre ciertos dominios; o declarar datos insuficientes. F4 continúa como referencia de sensibilidad, no como alternativa promovida si incumple la puerta humana.

## Secuencia resumida

**Congelar protocolo y particiones → verificar idioma/procedencia → medir señales aisladas → evaluar la matriz acotada → aplicar parada por futilidad → seleccionar una candidata → (si se autoriza, calibrar solo en desarrollo) → congelar todo → confirmar una sola vez con datos independientes.**

## Implementación de esta ronda de desarrollo

Esta implementación usa únicamente `validation/narrative-v1/development/` para los textos evaluados. Los documentos IA elegidos para el banco C2-v2 se retiran de la puntuación junto con todos los textos que compartan sus `prompt_id`; ningún perfil factorial puntúa los prompts utilizados como semillas. Los 120 textos humanos de desarrollo permanecen en el panel, con autor y obra agrupados.

El banco IA se selecciona de los ejemplos públicos ya existentes en el manifiesto de desarrollo, sin generar texto nuevo. El lock conserva ocho IDs, checkpoints, prompts, hashes y longitudes normalizadas. El banco humano usa ocho textos de dominio público de autores distintos, sin solapamiento con los autores humanos del desarrollo ni con los IDs de las semillas actuales de B0. Los perfiles confirmatorios deberán usar fuentes/modelos no usados en este desarrollo.

La auditoría lingüística actual contiene 404 casos revisados y 1.388 casos aún provisionales. El análisis primario de detección IA usa solo los textos españoles revisados del muestreo negativo con sus pesos de inclusión; los mixtos e ingleses se excluyen de esa estimación y los provisionales se informan aparte. El estimador ponderado es diagnóstico porque la selección fue estratificada por riesgo y prompt, no una confirmación independiente. La matriz y sus resultados no se usan para certificar ninguna puerta.

El factorial incluye P000/B0 y sus siete combinaciones L2, C2-v2 y M100-fallback50. F4 es una referencia adicional, no un noveno perfil factorial. El resultado de B0 en el panel íntegro se conserva aparte para comprobar la reproducción histórica; la comparación pareada usa el panel de desarrollo tras retirar los prompts de C2-v2.

### Ejecución y resultado de esta ronda

La matriz quedó implementada en `tools/f5_experiments/` y se ejecutó con:

```powershell
python -m tools.f5_experiments.run
python -m tools.f5_experiments.interactions
```

El runner lee el lock y el manifiesto factorial explícito de desarrollo, comprueba hashes de código/textos, excluye los prompts de semilla y guarda puntuaciones individuales, agregados y hashes. El análisis de interacción consume solo el resultado de desarrollo; mantiene los pesos del muestreo lingüístico y remuestrea por prompt/autor, con intervalos etiquetados como exploratorios. Ningún paso lee el conjunto reservado.

La ejecución produjo 1.896 puntuaciones factoriales y reprodujo B0/F4 en 1.912 textos de desarrollo. Ningún perfil pasó todas las puertas por punto estimado: P100/P110 conservaron FP humano 2,5% y cobertura 88,3%, pero fallaron detección en las ocho fuentes; M100 elevó la detección ponderada de español a más de 93%, pero produjo FP humano de 32,5–37,5% y cobertura de 34,2–39,2%. C2-v2 movió poco la detección (efecto factorial principal cercano a 1 pp). La combinación L2×M100 mostró una interacción negativa exploratoria en detección ponderada (−7,51 pp; IC bootstrap bilateral exploratorio −11,80 a −3,54); no se usa para promover ni ajustar parámetros.

Conclusión de esta ronda: **datos insuficientes para promoción y sin candidata viable con estas variantes**. Se mantienen umbral 15, margen 4 y B0 congelados. No se calibró ni se seleccionó usando la reserva. El informe legible, las salidas reproducibles y el lock están en `validation/f5-narrative-experiment-v1/`; véase `factorial-report.md` para métricas por fuente, sensibilidad y hashes.

### Decisión de cierre

El 25 de octubre de 2026 se cierra esta línea de investigación sin promover ninguna variante. No se ejecutará confirmación con el estado actual porque ninguna variante pasó las puertas puntuales en desarrollo y no existe un corpus independiente elegible. `f5-portable-v1`, B0, sus pesos y 15/4 permanecen disponibles como perfil optativo experimental, congelados. Reabrir investigación requerirá un mandato y protocolo nuevos; no convierte los resultados de desarrollo en confirmación.
