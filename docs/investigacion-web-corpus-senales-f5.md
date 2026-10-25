# Investigación web: corpus y señales adicionales para F5

**Fecha de consulta:** 25 de octubre de 2026

**Pregunta:** ¿hay una fuente pública nueva o resultados externos que cambien la decisión de continuar con las señales estructurales de F5 para narrativa en español?

**Uso:** investigación complementaria al cribado de desarrollo `f5-narrative-experiment-v1`; no se puntuaron textos nuevos ni se abrió ningún conjunto reservado.

## Hallazgos

### 1. ROBOT-TALK: excelente ajuste temático, pero los datos todavía no se descargan

El artículo del proyecto describe un corpus comparable de español con noticias, reseñas de cine y artículos científicos. Empareja textos humanos y generados por tema y longitud, y enumera una gama amplia de generadores, desde GPT-3 y GPT-4 hasta Gemini, Claude, Mixtral y DeepSeek. Eso lo hace una fuente prometedora para estudiar si las diferencias estilísticas sobreviven al emparejamiento por tema y tamaño. Sin embargo, la página del artículo informa explícitamente que los archivos de descarga aún no están disponibles. Tampoco contiene narrativa literaria ni humanos todos anteriores a 2020. Por ahora no puede funcionar como confirmación independiente de la población prioritaria.

Fuentes: [página del corpus en UCM](https://www.ucm.es/robottalk/corpus-robot-talk), [artículo del corpus en Alfinge](https://journals.uco.es/alfinge/article/view/18687?articlesBySimilarityPage=2). El artículo indica que los datos no están disponibles para descarga; su licencia editorial CC BY-NC-SA 4.0 aplica al artículo, y no debe asumirse que licencia los textos del corpus.

### 2. MedAID-ML: un posible control multilingüe, con acceso restringido y dominio distinto

MedAID-ML contiene textos biomédicos humanos y versiones generadas por GPT-4o, Mistral-7B y Llama 3.1 en español, inglés, alemán y francés. Sus autores describen 13.292 documentos multilingües y una partición temporal de prueba diseñada para reducir contaminación: textos humanos publicados en 2025 y checkpoints generativos de 2024. El registro indica que los ficheros están **restringidos** y que hay que solicitar acceso; no presenta una licencia reutilizable en los metadatos visibles. Además, es medicina/biomedicina, no narrativa. No se debe incorporar ni puntuar hasta recibir acceso y aclarar las condiciones de uso. Si se autorizara, serviría como control de transferencia de dominio, no como sustituto de la confirmación narrativa.

Fuentes: [registro de datos de TU Wien](https://researchdata.tuwien.ac.at/records/xr34x-tsp12), [repositorio oficial y descripción metodológica](https://github.com/Padraig20/MedAID-ML).

### 3. La literatura respalda señales estilísticas, pero también advierte sobre transferencia

Un estudio de clasificación con español, francés, alemán e inglés informa resultados altos cuando la evaluación se realiza en el corpus temático creado para el estudio. Esto justifica estudiar rasgos léxicos/documentales en español, pero sus cifras no demuestran que las mismas señales funcionen en narrativa histórica, fuentes nuevas o bajo un límite estricto de falsos positivos. ROBOT-TALK está diseñado expresamente para comparar rasgos lingüísticos y construye pares por tema y longitud; su indisponibilidad impide usarlo hoy.

En sentido contrario, el benchmark MAGE documenta dificultades de generalización fuera de dominio y entre generadores. Un estudio de límites de detectores informa sensibilidad a cambios de estilo y complejidad, con deterioro fuerte en ciertos estilos. La evidencia metodológica coincide con nuestro resultado: una característica puede separar muy bien un corpus concreto y, aun así, no constituir una señal portátil de autoría.

Fuentes primarias: [Schaaff et al., clasificación multilingüe](https://arxiv.org/abs/2312.04882), [MAGE, ACL 2024](https://aclanthology.org/2024.acl-long.3/), [Exploring the Limitations of Detecting Machine-Generated Text](https://huggingface.co/papers/2406.11073).

### 4. La evidencia de ficción en inglés no cambia la conclusión para el español

Un trabajo sobre ficción detectivesca clásica reporta más de 95% de exactitud en muestras cortas usando clasificadores sencillos. Es una señal de que una tarea narrativa puede contener diferencias observables. Sin embargo, es un estudio de otro idioma, un subgénero y una configuración de corpus concretos; no valida F5, las puertas acordadas ni transferencia a español. Lo trato como motivación para mantener abierta una futura réplica bien controlada, no como motivo para cambiar el resultado actual.

Fuente: [McGlinchey y Barclay, creative fiction](https://arxiv.org/abs/2412.15253).

## Decisión para el proyecto

La investigación web, por sí sola, **no aporta un corpus descargable apropiado** para confirmar narrativa española. Pero el cribado estructural nuevo sí modifica la decisión experimental: `validation/f5-structure-screen-v1/report.md` muestra que la familia fija de oraciones, puntuación, longitud de palabras y conectores elevó la detección OOF ponderada de **14,9%** (B0 + longitud) a **79,1%**, con 4,2% de falsos positivos puntuales; el delta agrupado exploratorio M2−M1 fue 64,2 pp. En ocho checkpoints de este banco, todos mejoraron ≥5 pp. La sensibilidad checkpoint-excluido fue favorable, aunque 18 de 68 prompts se comparten entre modelos, por lo que no equivale a transferencia a prompts nuevos.

La conclusión apropiada es **candidato para confirmación independiente**, no promoción ni cambio del producto. El límite superior bootstrap humano agrupado fue 7,5%, superior al máximo exigido de 5%, y hay solo 15 autores humanos. F5/B0 y el umbral/margen 15/4 permanecen intactos. El factorial previo de cambios internos L2/C2/M100 sigue sin candidato viable; el nuevo clasificador de rasgos estructurales es un experimento separado y no se ha integrado a F5.

El siguiente paso solo vale la pena si conseguimos un benchmark realmente independiente y legalmente utilizable. ROBOT-TALK sería el candidato prioritario cuando publiquen los datos, tras comprobar que los originales humanos, licencia, prompts y fuentes no solapan entrenamiento/desarrollo. MedAID-ML podría ser un estrés de transferencia biomédica si conceden acceso y se aclaran derechos, pero no resuelve la población literaria. Si ninguno se obtiene, la opción prudente es dejar esta línea sin promoción; no reemplazarla con otro análisis del mismo desarrollo.

Como dimensionamiento, Astra señaló que incluso 0 falsos positivos entre 15 autores deja una cota unilateral binomial del 95% cercana al 18%; para certificar una puerta de 5% hacen falta muchos más grupos independientes. Su aproximación binomial iid: 400 unidades humanas con tasa real FP 2% darían alrededor de 93,8% de probabilidad de certificar la puerta, y 150 prompts por fuente con detección real 90% darían cerca de 95,6% de potencia por fuente. Esos valores son guía de planificación y deben revisarse con el diseño agrupado real.

## Reglas de uso

- No extraer los textos de ROBOT-TALK desde las muestras web para construir una evaluación.
- No usar MedAID-ML mientras los archivos sigan restringidos o su licencia/permiso no esté confirmado.
- No tratar el año de publicación de un artículo como fecha de autoría de sus documentos; auditar fuente, fecha de cada texto, idioma, generación y licencia por separado.
- No cambiar umbral, margen, pesos o señales a partir de estos artículos.
- No declarar confirmación: esta nota resume evidencia pública; no añade observaciones a la evaluación.
