# Evaluación actual — f4-integridad

## Alcance

La auditoría de integridad encontró dos defectos en la evaluación anterior:
las semillas conservaban textos del grupo excluido y las medias por fold
contaban tasas sin denominador como ceros. Las cifras previas están archivadas
en [`historico/calibracion-f3.md`](historico/calibracion-f3.md) como registro
afectado; no son una validación independiente de f4.

Las reparaciones de segmentación y normalización cambian la señal del índice.
Se distingue por `version=f4-integridad`, sin cambiar pesos ni transformaciones.
No se recalibró con el holdout histórico ni se afirma eficacia de autoría.

## Procedimiento ejecutable

```bash
uv run python -B -m tools.calibrate
```

También funciona `python -B tools/calibrate.py`. El comando emite JSON por stdout,
no escribe archivos y **no evalúa el holdout por defecto**.

1. Carga y valida los 40 ids, clases, licencias no vacías, longitudes y SHA256
   reales de `corpus/manifest.csv` antes de puntuar.
2. Mantiene el split histórico: TRAIN de 34 piezas y holdout fijo
   `{h08,h16,h19,a05,a07,b03}`. El split es por ids; el grupo Zenodo cruza
   ambos lados, limitación histórica que impide presentarlo como separación
   completa por generador.
3. Forma 25 grupos TRAIN: autor humano, pieza narrativa IA y grupo Zenodo.
4. Para cada fold LOGO, reconstruye **ambas semillas** a partir de las fuentes
   históricas enumeradas en `corpus/seeds/manifest.json`, usando solo ids de
   calibración del fold. Excluye todo el grupo evaluado. Si no hubiera fuentes
   para una clase, falla en lugar de usar semillas globales o sintéticas.
5. Recalcula índices de calibración y de evaluación con esas mismas semillas
   del fold. El pipeline exige cinco checks; cobertura insuficiente produce
   abstención. La selección del umbral usa solo los casos de calibración.
6. Busca umbral 0..100 y margen en `{0,2,4,6,8}`. Maximiza balanced accuracy
   condicionada a no abstenerse; desempata por mayor cobertura, menor margen
   y cercanía del umbral a 50. Los candidatos sin casos evaluables de ambas
   clases se descartan. Optimizar una tasa condicionada exige leer siempre
   su cobertura: un resultado con muchas abstenciones puede parecer mejor.
7. Agrega matrices y predicciones fuera de muestra de todos los folds.
   TPR = TP/(TP+FN); TNR = TN/(TN+FP). Denominador cero produce `null`.
   No se promedian ceros de clases ausentes. La matriz cuenta abstenciones
   por clase y el informe incluye cobertura global y de cada clase.
8. Emite una elección exploratoria final sobre todo TRAIN, con las mismas
   fuentes históricas completas. **No modifica `tools/decision.py`.** Incluye
   huellas de manifiesto, léxico y semillas para reproducibilidad.

Las semillas completas de esta receta coinciden exactamente con los recursos
congelados usados por el CLI; la selección de sus fuentes es histórica, no una
optimización nueva. La evaluación interna sigue siendo exploratoria: corpus
pequeño, modelos/procedencias limitados y fuentes seleccionadas previamente.

## Regla de interpretación del CLI

`tools/decision.py` conserva 31/2 como **referencia histórica provisional**:
29..33 inclusivo implica abstención; valores menores se interpretan como sin
señal suficiente y mayores como estilo marcado. El diagnóstico comparte esa
misma regla y siempre emite `no_concluyente=True`. Las palabras internas
`humano`/`ia` de la evaluación son etiquetas de contraste, no veredictos.

## Holdout

Las dos aperturas históricas ya están consumidas. Este conjunto no puede
servir como prueba independiente de una señal corregida. Se mantiene una
ruta explícita de reproducción con `--evaluar-holdout`, que avisa de esa
limitación; no se ejecutó durante esta reparación. Para validar f4 se necesita
un corpus y holdout nuevos, declarados antes de su evaluación.

## Evaluación externa realizada

Se añadió external-v1, separado de corpus/ y de las semillas: 90 fragmentos
humanos de nueve ediciones de 2018, 200 relatos IA publicados y 300 generaciones
literarias adicionales. Se congeló la selección y se evaluó f4 sin ajustar sus
parámetros. Hay ocho falsos positivos humanos y cobertura cero en el panel
aplanado de 300 textos. Ver [informe completo](validacion-externa-v1.md). El
conjunto queda consumido para nuevas optimizaciones; no se alteró el holdout previo.
