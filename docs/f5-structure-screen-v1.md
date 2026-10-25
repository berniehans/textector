# Protocolo de cribado: señales estructurales para F5

**ID:** `f5-structure-screen-v1`

**Estado:** congelado antes de ejecutar el scorer experimental

**Objetivo de uso:** cribado exploratorio de desarrollo; no confirma promoción ni autoría.

## Pregunta y decisiones

¿Un conjunto fijo de rasgos estructurales de prosa narrativa en español agrega señal predictiva a la puntuación continua de F5, después de controlar explícitamente longitud, cuando se evalúan autores y prompts no vistos?

- **H0 (operacional):** añadir estructura a `B0 + longitud` no mejora la detección agrupada fuera de muestra en al menos 5 puntos porcentuales, medida a un umbral operativo con FP humanos de entrenamiento ≤5%; o la ganancia depende de longitud/formato o no aparece en las fuentes.
- **H1 (operacional):** `B0 + longitud + estructura` mejora al menos 5 puntos sobre `B0 + longitud` en detección IA española ponderada, sin aumentar FP humanos fuera de muestra por encima de 5%, y la mejora tiene el mismo signo en al menos 6 de las 8 fuentes.
- **Contrahipótesis:** cualquier aparente mejora estructural se explica por longitud, fuente/checkpoint, patrón de prompt, estilo del dominio o decisiones del umbral; no es una señal portable.

Estas hipótesis solo autorizan un cribado de la familia preespecificada. Con la muestra agrupada disponible no se puede demostrar la imposibilidad general de detectar texto generado ni certificar las puertas de producto.

## Población, datos y exclusiones

- Única entrada de puntuación: `validation/f5-narrative-experiment-v1/factorial-development-manifest.jsonl`, que apunta explícitamente a textos de `validation/narrative-v1/development/texts/` y excluye prompts usados por el banco C2-v2.
- Humanos: todos los casos narrativos de desarrollo elegibles; grupos de partición y remuestreo por autor (`author_or_model`; obra como comprobación de sensibilidad).
- IA primaria: solamente filas con auditoría manual de idioma `espanol`, usando su probabilidad de inclusión y peso de muestreo; grupos por `prompt_id`. Las filas inglesas, mixtas y de idioma provisional quedan fuera del estimando primario.
- Fuentes: ocho checkpoints declarados en el manifiesto. El análisis por fuente se publica completo, sin elegir modelos según resultados.
- No leer `validation/narrative-v1/reserved/`, `validation/reserved-f5-v1/`, scores ni resultados de reserva, ni manifiestos que contengan textos reservados. No usar IberAuTexTification como conjunto nuevo: ya fue evaluado y sus textos aplanados no permiten rasgos de párrafo.
- Cualquier texto sin etiqueta manual española, autor/prompt, hash coincidente o al menos 50 tokens/150 bytes se excluye del estimando primario y se cuenta por motivo.

## Variables congeladas

Se usa F5/B0 como una única variable basal continua y se mantienen sin cambios su score, umbral 15, margen 4, pesos, léxico, semillas, normalización y abstenciones. El umbral/margen solo describen la decisión F5 original; el modelo estadístico diagnóstico usa un corte interno distinto, estimado exclusivamente dentro de los grupos de entrenamiento de cada partición, con el objetivo de controlar FP.

**Control de longitud:** logaritmo natural del número de tokens y logaritmo natural de bytes limpios, calculados después de la normalización/tokenización del proyecto.

**Familia estructural, fijada antes de puntuar:**

1. Media, mediana, desviación estándar y coeficiente de variación de tokens por oración.
2. Número de oraciones por 100 tokens.
3. Longitud media y desviación estándar de caracteres por token.
4. Densidad por 100 tokens de coma, punto y coma, dos puntos, raya/guion, signos `¿?¡!` y elipsis.
5. Densidad por 100 tokens de una lista cerrada de conectores discursivos en español codificada en el script.

No se utilizan límites de párrafo, saltos de línea, TTR/MATTR (MATTR ya integra B0), embeddings, vocabulario aprendido, selección de variables, optimización de hiperparámetros ni ingeniería posterior al resultado. Ambos grupos reciben la misma normalización de espacios; los rasgos se extraen del texto normalizado conservando solo puntuación que sobreviva.

## Modelos diagnósticos comparados

1. **M0:** regresión logística regularizada con solo score B0; control de referencia para el cribado, no una versión de producto.
2. **M1:** `B0 + longitud`.
3. **M2:** `B0 + longitud + familia estructural`.

No se entrenan modelos de lenguaje ni se instalan dependencias. El escalado se ajusta solo sobre entrenamiento. La regresión logística usa L2 fija (`C=1`) y ponderación por clase; no se busca C ni se eligen rasgos por rendimiento.

## Particiones y evaluación

- Cinco pliegues externos deterministas, agrupados por autor humano y por `prompt_id` IA; un grupo nunca aparece a ambos lados del mismo pliegue.
- Para cada pliegue externo, escoger el corte operativo con predicciones internas fuera de grupo dentro del entrenamiento: cuatro pliegues internos agrupados, modelo reentrenado en cada corte. El corte maximiza detección IA ponderada sujeto a FP humanos ponderados ≤5% en la predicción interna. El pliegue externo permanece aislado hasta puntuar.
- Los pliegues se equilibran de forma determinista por número de filas de cada clase y número de grupos. Toda transformación estadística se ajusta dentro del pliegue de entrenamiento.
- Los errores y abstenciones F5 quedan disponibles como controles descriptivos. Para una comparación sobre casos elegibles, no se imputan scores F5 insuficientes; se excluyen antes de generar particiones y se informa su cantidad.
- Métrica primaria: diferencia M2−M1 de detección IA sobre todas las filas IA del panel primario, ponderada por la probabilidad de inclusión de la auditoría. Reportar también detección por checkpoint y macro por prompt.
- Métricas de seguridad: FP humano sobre todos los humanos y cobertura/eligibilidad; los humanos reciben peso total igual por autor. Reportar además valores por fila y número de grupos.
- Métricas secundarias: ROC-AUC OOF ponderado, puntos de operación por pliegue, abstenciones F5 y diagnóstico del panel no español/provisional separado.
- Intervalos descriptivos al 95% por bootstrap de grupos (autor para humano, prompt para IA; prompts emparejados a través de checkpoints). No son certificados de promoción debido al pequeño número de autores, auditoría estratificada y cortes estimados.

## Regla de decisión

- **Candidato a confirmación independiente:** M2 supera M1 en ≥5 pp de detección IA ponderada OOF, pasa FP humano ≤5% y cobertura ≥80% puntuales, mejora en ≥6/8 fuentes y no se explica por el control `M1`. Esto solo permite diseñar una evaluación nueva; no promueve F5 ni cambia 15/4.
- **No-go para esta familia/configuración:** no se observa una mejora de 5 pp y reproducible sobre M1, cualquier ganancia se concentra en una sola fuente, o falla claramente una puerta humana. Se cierra el cribado actual; no se declara imposible la detección general.
- **Insuficiente:** errores de integridad, pocos grupos/fuentes, inestabilidad del corte o intervalos demasiado amplios impiden discriminar. Se puede detener por coste/valor esperado, sin llamarlo refutación.

## Integridad y desviaciones

El runner comprueba hashes de texto y límites de ruta antes de leer. El hash del protocolo, manifiesto, etiquetas de idioma y código se registra en resultados. El runner no admite argumentos de rutas a corpora ni búsqueda recursiva. No se escriben ni modifican pesos, umbral/margen F5 o archivos de reserva.

La revisión de Astra (GPT-6 Astra) advirtió que IberAuTexTification ya estaba evaluado y que hay 15 grupos humanos: incluso 0 FP entre esos 15 autores deja una cota unilateral aproximada de 18,1%, muy por encima de la puerta 5%. Por eso esta pantalla no puede aprobar promoción aunque la tasa puntual sea buena.
