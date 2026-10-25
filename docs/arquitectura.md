# Arquitectura

`tools/cli.py` lee texto y recursos y presenta el informe. `tools/pipeline.py`
orquesta los cinco checks y aplica la misma política de cobertura para CLI y
calibración. Con menos de cinco checks disponibles el pipeline se abstiene;
`scoring.compute_indice` conserva su contrato general de renormalización.

`textector_core.tokenize` aplica NFC, eliminación de invisibles y casefold antes
de extraer tokens. `split_sentences` conserva spans sobre el original; descarta
cabeceras y trata elipsis de forma conservadora. `uniformity` y `estructura`
admiten saltos LF/CRLF. Cada check es puro, con métricas crudas y señal [0,1].

`scoring.py` conserva los pesos y topes históricos de `f4-integridad`. F5 se implementa en `tools/f5.py` con perfil separado `f5-portable-v1`, índice de denominador fijo y checks de ritmo/estructura fuera del score.
Las reparaciones de preprocesado cambian la señal; no se reutilizan resultados
históricos como validación independiente.

`decision.py` centraliza la referencia provisional 31/2 y la abstención centrada
inclusiva. `diagnostico.py` cruza la prosa con el eje `estructura.py`; todas las
categorías son descriptivas y no concluyentes.

`resources.py` resuelve el léxico y semillas desde el checkout o los recursos
incluidos en el wheel mediante `importlib.resources`. Un checkout incompleto
falla cerrado. El CLI acepta un léxico externo validado y registra su huella.

`calibrate.py` valida el manifiesto real, reconstruye las semillas por fold sin
el grupo evaluado y agrega matrices fuera de muestra. La elección del umbral
se hace solo con calibración del fold. Su ejecución por defecto usa TRAIN y
mantiene cerrado el holdout histórico. No modifica los parámetros del CLI.

Los módulos de ejecución usan solo stdlib. La construcción usa hatchling y el
wheel distribuye todos los recursos necesarios para analizar textos. La CI prueba
Python 3.11/3.13 en Windows/Linux, el checkout y la instalación independiente.
