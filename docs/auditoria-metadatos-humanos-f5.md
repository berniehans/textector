# Auditoría preliminar de metadatos humanos para F5

**Fecha:** 25 de octubre de 2026

**Uso:** preparación de una futura confirmación independiente; todavía no se han elegido fragmentos ni ejecutado F5 sobre estas fuentes.

**Seguridad del procedimiento:** solo se descargaron cuatro archivos públicos de metadatos. No se descargaron textos de los candidatos ni se abrieron archivos reservados.

## Snapshots y huellas de los metadatos

| Corpus | Revisión fuente | Recurso de metadatos local | SHA-256 | Filas / observación |
|---|---|---|---|---|
| CoNSSA | `cligs/conssa@8fccf669ed1bdbad309ff190f5afb0d6066d70a3` | `validation/narrative-v2-corpus-audit/source-metadata/conssa-metadata.tsv` | `2c127dbb6f82b33548151e09a5a185a384c36981eb14e7fd1c7cfab54f035400` | 358 obras en el catálogo; 217 marcadas `free`; 39 autores distintos en esas obras disponibles. |
| ELTeC-spa | `COST-ELTeC/ELTeC-spa@83e2a22d5ef66f96e59f47f7ef810358c4236322` | `validation/narrative-v2-corpus-audit/source-metadata/eltec-spa-metadata.tsv` | `ffcee033007c2a239f3046ee71ef089687e398ee6103a27a11ad22b6931fb3cb` | 100 registros y 63 nombres normalizados como autores en el snapshot `master`; la edición v0.9.1 de 2021 es otra versión con 84 novelas. |
| Conha19 | `cligs/conha19@d5def0a3b5900fd37172714d1b8b91bfce0a267c` | `validation/narrative-v2-corpus-audit/source-metadata/conha19-metadata-free.csv` | `e38f930cdbbf07686bbd6c49df1790894f97d464530ac41109570488bd8086d2` | 237 registros `free`, 114 etiquetas abreviadas de autor; necesitan resolución de identidad antes del conteo final. |
| Conha19 | mismo snapshot | `validation/narrative-v2-corpus-audit/source-metadata/conha19-metadata-all.csv` | `975d4dcae3c2721caf5b572b77a4144b80d5215de871b77a83a79ef8b59e8ebc` | Archivo complementario del catálogo total; no se usa para afirmar que las obras restringidas son reutilizables. |
| Gutendex / catálogo de libros en español | Respuesta local ya archivada de `work/corpus-scout/gutendex-es-all.json` | `work/corpus-scout/gutendex-es-all.json` | `1a77aef20110ab5188f3c561c25712ccf12680b6a3dc7a4fc10676b4524f005a` | 922 registros; la búsqueda por materias/colecciones señala 537 posibles obras narrativas y 192 autores; 154 no coinciden literalmente con la exposición previa. |

Los tres commits son snapshots inmutables anotados para reproducibilidad. No mezclar versiones distintas del mismo catálogo. La auditoría externa de corpus documenta las fuentes oficiales y las licencias declaradas; CoNSSA declara dominio público para textos publicados y CC BY para metadatos/marcado. ELTeC-spa declara textos en dominio público. Para Conha19, el registro de Zenodo indica que sus archivos están restringidos; el CSV `metadata_free` del repositorio no basta para acreditar licencia/permiso del texto de cada fila. Se excluye de la reserva hasta comprobar derechos y procedencia por texto.

## Cruce preliminar con autores ya expuestos

Se tomaron los autores explícitos de `corpus/manifest.csv`, `validation/narrative-v1/development/manifest-human.jsonl` y el panel humano de `validation/external-v1/manifest.jsonl`, además de nombres que la documentación no reservada identifica como expuestos en la reserva anterior. El primer cruce automatizado normaliza tildes, puntuación y paréntesis, y añade una revisión difusa para orden `apellido, nombre` y seudónimos obvios.

- El inventario combina 46 cadenas históricas, que se reducen a 44 por normalización básica; los alias y seudónimos aún requieren canonización.
- El inventario revisado combina 46 cadenas históricas y 43 identidades tras normalización y aliases conocidos; siguen pendientes alias más complejos y revisión manual.
- En las 39 identidades CoNSSA con obras `free`, el cruce reproducible detecta 15 ya expuestas y deja 24 no coincidentes de forma exacta. Hay además autores repetidos entre CoNSSA y ELTeC.
- ELTeC-spa tiene 62 nombres canónicos en este snapshot; 15 coinciden con la exposición conocida tras invertir nombres catalogados como `apellido, nombre`, y 47 no coinciden literalmente.
- Gutendex tiene 922 registros y 192 identidades con etiquetas de narrativa; 154 no coinciden literalmente con autores expuestos. Las materias son un filtro candidato, no una etiqueta editorial validada. Algunos registros son traducciones, resúmenes, historia literaria o ediciones que deben excluirse individualmente.
- Después de quitar coincidencias conocidas y duplicados directos entre CoNSSA, ELTeC-spa y Gutendex, quedan **210 identidades candidatas brutas** antes de revisión bibliográfica. Este número no equivale a autores confirmados nuevos. No basta para declarar 400 autores independientes; sí permite planificar 400 fragmentos si se muestrean varios por autor, pero entonces los intervalos deben agrupar correctamente por autor/obra y pueden no sostener la puerta estadística.
- En Conha19, `author-short` (p. ej., apellido e iniciales concatenadas) no se puede comparar de forma confiable contra nombres completos mediante normalización literal. Se necesita un crosswalk bibliográfico; no se cuentan sus 114 rótulos como 114 autores nuevos.
- Los catálogos pueden solaparse entre sí. La deduplicación final debe cruzar autor canónico, títulos/seudónimos, IDs de catálogo, hashes de obra completa y huellas de fragmentos. Una obra distinta del mismo autor también queda fuera de una confirmación de autores no vistos.

Por estas razones **no se publica todavía una cifra de autores nuevos ni un lock de muestra**. Estos metadatos son un punto de partida para selección y auditoría, no una muestra aprobada. Tampoco se incorporan los conteos de filas como si fueran unidades independientes: la unidad humana para el análisis de FP y su intervalo será autor, con obras anidadas en autor.

La auditoría se volvió a ejecutar después de fijar los SHA-256 esperados en `tools/audit_human_candidate_metadata.py`; todos los snapshots enumerados arriba pasaron la verificación. La repetición reprodujo los conteos de catálogo y exposición (CoNSSA: 39 autores en 358 filas, 15 expuestos; ELTeC-spa: 62 autores, 15 expuestos; Conha19: 237 filas libres y 114 claves de autor sin resolver; Gutendex: 192 autores candidatos y 154 no coincidentes literalmente). Esto valida la integridad de estos archivos de metadatos y del cálculo reproducible, no la identidad final de los autores, la elegibilidad de cada título ni los derechos de cada texto.

## Fuentes oficiales

- [CoNSSA: repositorio, alcance y licencias](https://github.com/cligs/conssa)
- [ELTeC-spa: repositorio, versiones y dominio público](https://github.com/COST-ELTeC/ELTeC-spa)
- [Conha19: registro Zenodo y restricciones de acceso](https://zenodo.org/records/4447468)
- [Project Gutenberg: licencia y términos del material distribuido](https://www.gutenberg.org/policy/license)
