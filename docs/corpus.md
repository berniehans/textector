# Corpus y semillas

El corpus contiene 40 piezas: 20 extractos humanos de Project Gutenberg
(`human/h01..h20`), 10 narraciones producidas por un agente/modelo (`llm/a01..a10`)
y 10 piezas de noticias sintéticas Zenodo (`news/b01..b10`). Procedencias,
autores/modelos y licencias declaradas figuran en `corpus/manifest.csv` y NOTICE.
Esta reparación no vuelve a certificar las fuentes externas ni sus licencias.

## Integridad de archivos

`chars` cuenta caracteres del texto UTF-8/LF; `SHA256` corresponde a los **bytes
UTF-8/LF versionados**. La carga valida hashes, longitudes, ids y metadatos.
Las pruebas comparan también hashes reales, no solo su formato.

Se corrigieron los hashes h14..h20: correspondían a CRLF, mientras Git distribuye
LF conforme a `.gitattributes`. No se alteró ninguna palabra ni pieza del corpus.

## Semillas históricas preservadas

`corpus/seeds/manifest.json` fija ids, orden, separador, bytes y SHA256:

- IA: a01, a02, a03, a04, a06, a08, a10.
- Humana: h01, h02, h05, h06, h07, h09, h10.

Cada archivo es concatenación exacta de esas piezas, unidas por `\n\n`.
Las semillas **no contienen todo TRAIN**. Sus bytes no cambiaron durante f4.
Ningún id del holdout aporta material. La selección histórica de estas fuentes
no se presenta como una selección óptima ni independiente del desarrollo previo.

El CLI usa esos recursos congelados. La LOGO-CV reconstruye el subconjunto de
fuentes permitido en cada fold, retirando todo el grupo evaluado de las semillas.
El informe registra las fuentes y huellas por fold.

## Split y límites

TRAIN contiene 34 piezas. Holdout histórico fijo: h08, h16, h19, a05, a07, b03.
Los grupos TRAIN corresponden a autor humano, pieza narrativa IA y grupo único
Zenodo. Pereda reúne h14 y h17. Zenodo cruza TRAIN y holdout: el split histórico
no ofrece aislamiento total por generador. El holdout ya fue utilizado y no se
evalúa por defecto. Nueva validación de f4 requiere corpus y holdout nuevos.

Ver [evaluación](calibration.md) y [registro histórico](historico/calibracion-f3.md).
Toda pieza futura debe tener procedencia, licencia, checksum y modelo/prompt
cuando corresponda. No ajustar el holdout después de ver resultados.

## Evaluación externa realizada

Se añadió external-v1, separado de corpus/ y de las semillas: 90 fragmentos
humanos de nueve ediciones de 2018, 200 relatos IA publicados y 300 generaciones
literarias adicionales. Se congeló la selección y se evaluó f4 sin ajustar sus
parámetros. Hay ocho falsos positivos humanos y cobertura cero en el panel
aplanado de 300 textos. Ver [informe completo](validacion-externa-v1.md). El
conjunto queda consumido para nuevas optimizaciones; no se alteró el holdout previo.
