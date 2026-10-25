# Reparación de integridad — f4

Paquete 0.2.0, método `f4-integridad`. Se conservaron pesos, transformaciones,
corpus textual y bytes de las semillas; se identificó la señal corregida con
una versión nueva porque segmentación y normalización pueden cambiar índices.

| Hallazgo | Reparación |
|---|---|
| Wheel sin recursos | Léxico y semillas incluidos; carga por importlib.resources; smoke de instalación real fuera del checkout |
| Semillas con datos del fold evaluado | Reconstrucción por fold limitada a fuentes permitidas; índices de ambos lados recalculados |
| Tasas ausentes tratadas como cero | Matriz agregada fuera de muestra, null cuando no hay denominador y cobertura por clase |
| Umbrales incoherentes | Una regla provisional 31/2; banda 29..33 inclusiva; ninguna categoría concluyente |
| Hashes CRLF frente a LF | Siete hashes corregidos al contrato UTF-8/LF; validación de bytes y longitudes al cargar y en tests |
| Configuración vacía/inválida | Esquema explícito, versión admitida y listas no vacías; rechazo con error limpio |
| Puntuación sin palabras | Cobertura insuficiente sin StatisticsError |
| Cierres y elipsis | Spans sin pérdida de caracteres; elipsis ASCII/Unicode sin cortes |
| Estructura insuficiente y bonus | Mínimo dos secciones con contenido; números de cabecera separados del título |
| Unicode y saltos | Tokenización NFC y sin invisibles; LF/CRLF equivalentes |
| Semillas vacías | Rechazo tanto en carga como en el check inyectado |
| Script calibrate directo | Arranque resuelto; holdout cerrado por defecto |
| Atribución del léxico | Etiquetas de inspiración temática explícitas; frases y pesos preservados |
| Reproducibilidad | Manifiesto exacto de semillas; hashes de entradas y fuentes en evaluación; tests de regresión y CI del wheel |

## Alcance pendiente de investigación

La reparación hace ejecutable y comprobable el programa; no demuestra detección
de autoría. La selección de semillas y el pequeño corpus siguen siendo históricos.
Las cifras previas de CV se archivan con sus defectos, sin presentarlas como
evidencia independiente. No se abrió el holdout durante esta reparación. Un
corpus y holdout nuevos son necesarios antes de afirmar generalización de f4.

Los tests incluyen reproducción de las entradas que fallaban, fronteras 0..100,
huellas reales, aislamiento por fold y tasas con clases ausentes. El smoke del
wheel crea un venv, instala sin dependencias ni red y comprueba el entry point,
los recursos y paridad JSON con el checkout.
