# Validación externa de textector — corpus nuevo

25 de octubre de 2026. Método **f4-integridad**, umbral 31, margen 2,
banda de abstención inclusiva 29..33. **No se generó ningún texto IA nuevo**
ni se ajustó el detector a estos resultados.

## Resultado principal

El proyecto tiene una señal útil para los relatos infantiles sintéticos de esta
muestra, pero **no queda validado como detector general de autoría**: marca ocho
fragmentos humanos como IA y se abstiene ante el formato aplanado del segundo
corpus IA. La comparación entre literatura histórica y relatos infantiles es
una prueba limitada de transferencia entre estilos, no una prueba controlada de
autoría a igualdad de género, longitud, época y modelo.

| Panel | N | Señal IA | Sin señal suficiente | Abstención |
|---|---:|---:|---:|---:|
| Libros humanos anteriores a 2020 | 90 | **8 falsos positivos** | 63 | 19 |
| Relatos españoles de Gemini 1.5 Flash, ya publicados | 200 | 190 | 1 falso negativo | 9 |
| Narrativa española IberAuTexTification, seis códigos de modelo | 300 | — | — | **300 por insuficiencia** |

En los humanos, los falsos positivos son **8/90 = 8,9%** del total. Entre los
71 casos en que el programa decide, son **8/71 = 11,3%**; la especificidad
condicionada es **63/71 = 88,7%** y la cobertura de decisión **71/90 = 78,9%**.
De sus 19 abstenciones, 14 son por cobertura insuficiente y 5 por banda.

En Gemini, detecta **190/200 = 95% del total**, con 9 abstenciones. La sensibilidad
condicionada a los 191 casos decididos es **190/191 = 99,5%**. Esa segunda tasa
no debe presentarse sin el total y las abstenciones, ni extrapolarse a otros
generadores o a narrativa adulta.

IberAuTexTification no tiene una sensibilidad medible con este pipeline: ninguno
de los 300 casos alcanza los cinco checks. No se cuentan como falsos negativos ni
como aciertos. `uniformity` es insuficiente en 300 y `burstiness` en 296; pueden
coexistir varios checks insuficientes por texto. El archivo publicado no conserva
saltos de párrafo. No se añadieron párrafos ni se alteró el detector para puntuarlo.

## Procedencia del corpus

### Humanos: nueve obras, nueve autores, 90 fragmentos

Se fijó cada texto a un **commit de GITenberg fechado en 2018**, anterior al límite
de 2020. Los archivos conservan las cabeceras de Project Gutenberg y su atribución.
Esto ofrece evidencia documental de que esas versiones digitales ya existían
antes del corte; no se usa la fecha actual de subida de una copia como si fuera
la fecha de creación de una obra.

Cada obra aporta diez extractos de párrafos completos, con objetivo de unas 250
palabras y posiciones deterministas repartidas por el cuerpo. Se conserva su
ortografía y puntuación. La mediana de extensión humana es aproximadamente 271
tokens; los relatos TinyStories rondan 121: la longitud sigue siendo un factor
de confusión. La unidad de procedencia es la obra/autor, no cada fragmento como
si fuera una observación independiente.

| Obra y versión fijada | Autor | Snapshot | Sin señal | Señal IA (FP) | Abstención |
|---|---|---|---:|---:|---:|
| [Niebla](https://github.com/GITenberg/Niebla-Nivola_49836/tree/b669cb60d852db11157f35fa3d7a81a55e44d4da) | Miguel de Unamuno | 2018-10-06 | 8 | 1 | 1 |
| [Cuentos de Amor de Locura y de Muerte](https://github.com/GITenberg/Cuentos-de-Amor-de-Locura-y-de-Muerte_13507/tree/50c370e17fd68100aeb11997169f05d925e8628c) | Horacio Quiroga | 2018-10-20 | 8 | 1 | 1 |
| [Mala Hierba](https://github.com/GITenberg/Mala-Hierba_43017/tree/fc9d3afd65f18ab9dded48b0b4d13583049377e3) | Pío Baroja | 2018-10-08 | 9 | 0 | 1 |
| [Mare nostrum](https://github.com/GITenberg/Mare-nostrum_23236/tree/1281c5c89073f478241af622f957a860275815aa) | Vicente Blasco Ibáñez | 2018-10-18 | 8 | 1 | 1 |
| [Sonata de otoño; Sonata de invierno](https://github.com/GITenberg/Sonata-de-oto-o--Sonata-de-inviernomemorias-del-Marqu-s-de-Bradom-n_46182/tree/5ffc11c298c3e2fc2bfb27bfdd31b283283900c0) | Ramón del Valle-Inclán | 2018-10-06 | 6 | 3 | 1 |
| [Azul...](https://github.com/GITenberg/Azul-Obras-Completas-Vol-IV_52894/tree/cfefa927c27518c569c74d2e0d41a9bf3f8467d3) | Rubén Darío | 2018-09-20 | 7 | 0 | 3 |
| [Amistad funesta](https://github.com/GITenberg/Amistad-funestaNovela_18166/tree/fa0ee4454d0d6f3c1013def46c5602bb14c20dfd) | José Martí | 2018-10-19 | 3 | 0 | 7 |
| [La gloria de don Ramiro](https://github.com/GITenberg/La-gloria-de-don-Ramirouna-vida-en-tiempos-de-Felipe-segundo_29920/tree/49ec09fb304a4a0203b5b3cc331ad06a25a944df) | Enrique Larreta | 2018-10-18 | 8 | 0 | 2 |
| [Platero y yo](https://github.com/GITenberg/Platero-y-yo_39209/tree/c0a1d3871f88ed43e5225ebb5ecad4f3b80224af) | Juan Ramón Jiménez | 2018-10-16 | 6 | 2 | 2 |

Control de calidad **antes de puntuar**: se excluyó la edición de *La Navidad en
las Montañas* por sus anotaciones inglesas intercaladas. En *Azul...* se delimitó
la prosa de Darío, retirando el prólogo de Juan Valera —autor ya presente en el
corpus anterior— y el bloque de poesía. En *Amistad funesta* se retiró la extensa
introducción de Gonzalo de Quesada. Los límites y offsets son reproducibles desde
las fuentes fijadas. La normalización CRCRLF→LF corrige el formato del mirror,
sin convertir cada línea tipográfica en un párrafo.

### IA: fuentes existentes, sin generación durante esta tarea

1. **[robrenaud/multilingual_tinystories](https://huggingface.co/datasets/robrenaud/multilingual_tinystories)**,
   revisión `785db5c10f23ba13893cbe692943d656170dadb8`, archivo `stories_01.json`.
   Se descargó un prefijo de 4 MiB con respuesta HTTP 206 y rango verificado.
   De sus primeros 1.000 registros completos se eligieron 200 por orden de hash
   determinista. Se evaluó el campo español `story`, no la traducción inglesa.
   Los registros declaran `source=gemini-1.5-flash` e instrucciones de cuentos
   infantiles de 3 a 5 párrafos. No son instrucciones del usuario de este chat.
   La procedencia de generación es la declarada por el publicador; no se dispone
   de una auditoría independiente de sus llamadas al modelo. Licencia declarada:
   Apache-2.0.
2. **[Genaios/iberautextification](https://huggingface.co/datasets/Genaios/iberautextification)**,
   revisión `5c1c380eb27b7a73bb75ee6239ff25db10c144ae`, archivo
   `data/subtask_1/train.tsv`. Se escogieron 50 generaciones `es/literary` por cada
   código A..F, con prompts distintos y muestreo por hash. El nombre `train` es
   el split del proveedor; **textector no se entrenó con él**. La publicación
   identifica seis generadores, pero estos registros usan códigos: no se inventó
   una equivalencia A..F con nombres de modelo. Licencia declarada por la ficha
   original: CC-BY-NC-ND-4.0. Se conservaron los textos tal como se publican.

El resultado alto en TinyStories puede deberse en parte a vocabulario sencillo,
frases y párrafos regulares, justamente lo que inducen sus prompts. Es evidencia
sobre ese panel, no sobre todos los textos IA. El otro panel impide afirmar que
se hayan validado seis modelos adicionales.

## Integridad y separación de la evaluación

- **590/590 hashes de textos correctos**; fuentes fijadas por revisión, archivo
  y posición. Se restauraron los 590 textos desde los archivos de origen y todos
  reprodujeron exactamente sus SHA256, sin volver a puntuar para elegir casos.
- Selección y protocolo congelados antes del primer scoring. Se registraron en
  la ejecución los hashes de ambos antes de evaluar. No se seleccionaron ejemplos
  por su índice ni se descartaron entradas por la cobertura del detector.
- Se excluyeron duplicados exactos, coincidencias de 20 tokens consecutivos con
  el corpus/semillas previos y duplicados casi idénticos definidos en el protocolo.
  Una generación se descartó por prompt repetido; la otra exclusión fue la edición
  humana anotada. Los 590 seleccionados no tienen ese solapamiento con el corpus
  anterior. Esto no demuestra ausencia de dichos libros en el preentrenamiento
  de los LLM proveedores, algo que no se puede comprobar aquí.
- Pesos, léxico, semillas, preprocesado y umbrales permanecieron idénticos a sus
  huellas congeladas. El holdout anterior no se puntuó. El corpus nuevo no se
  incorporó a semillas ni a calibración.
- Bootstrap descriptivo por autor/obra (9 grupos, 2.000 remuestreos): intervalo
  percentil 95% de especificidad condicionada **81,3%..96,1%**. No trata los 90
  fragmentos como observaciones humanas independientes; nueve autores siguen
  siendo pocos para generalizar.
- Tras esta ejecución, **external-v1 queda consumido como benchmark**. Se puede
  reproducir; si se ajusta el método mirando estos resultados, hará falta otro
  conjunto no utilizado para validar la mejora.

## Reproducción

Los textos seleccionados se guardan localmente en
`validation/external-v1/texts/`. Se excluyen de Git, junto con las descargas;
el protocolo, manifiesto, fuentes y resultados sí quedan versionables.

```bash
# Restaura datos públicos, comprueba hashes y no ejecuta código del proveedor.
python -B tools/fetch_external_corpus.py

# Reproduce una evaluación ya consumida; no aporta una validación nueva.
python -B tools/validate_external.py --output reproduccion.json

python -B -m unittest discover -s tests -p "test_*.py" -v
```

La restauración puede descargar unos 137 MB de IberAuTexTification, el prefijo de
4 MiB y las nueve ediciones humanas. Las condiciones de los textos se mantienen
separadas de la licencia MIT del código. El kit reproducible incluye metadatos,
resultados y scripts; no redistribuye textos de terceros ni las descargas completas.

Pruebas del proyecto tras añadir las herramientas: **153 pasan en Python 3.11.15**.
Los ocho falsos positivos y todas las abstenciones permanecen en los resultados.

## Huellas de la evaluación

- Protocolo: `d51cbdf56f28b672e891c1d848f79f34191b1bf809982b113e39ba9f556e1403`.
- Manifiesto de selección: `3a9d90456ad8cb885c00a1ef812e2367c51243f8ad534320aff239671eb151ac`.
- Evaluador ejecutado: `9be2bf7dd4e4315210e16b634de935b71fdcb2e6432396095be4b9dce57de29f`.

Los hashes de cada fuente del detector y de cada pieza se encuentran en
`protocol.json`, `sources.json` y `manifest.jsonl`. Las decisiones por caso y los
agregados completos están en `results.json`.
