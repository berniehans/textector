# Guía de uso

[Índice documental](README.md) · [Presentación en español](../README.es.md) · [Arquitectura](arquitectura.md)

textector **0.3.1** requiere Python **3.11+**. El análisis utiliza biblioteca estándar, se ejecuta localmente y no necesita claves de API ni acceso a servicios externos.

## Instalación

### Versión publicada

```bash
python -m pip install "https://github.com/berniehans/textector/releases/download/v0.3.1/textector-0.3.1-py3-none-any.whl"
textector analyze --archivo texto.txt --detallado
```

El wheel incluye léxico, configuración F5 y ambas semillas. Puede ejecutarse fuera del checkout y no necesita el corpus completo. Se distribuye por [GitHub Releases](https://github.com/berniehans/textector/releases/tag/v0.3.1); no se presupone un paquete de PyPI.

### Desde el repositorio

```bash
git clone https://github.com/berniehans/textector.git
cd textector
uv sync --locked
uv run python -B tools/cli.py analyze --archivo corpus/human/h01.txt
uv run python -B tools/cli.py analyze --archivo texto.txt --json --diagnostico
```

`uv` y el backend de construcción son herramientas de desarrollo; la ejecución del programa instalado no incorpora dependencias externas.

## Preparar la entrada

Usa texto UTF-8. Conserva párrafos y puntuación originales: no añadas saltos artificiales para conseguir que F4 puntúe. `--archivo` es la opción más directa para preservar codificación y formato, especialmente en Windows. La entrada estándar depende también de la codificación de la terminal.

| Perfil | Condiciones mínimas |
|---|---|
| F4, predeterminado | Cinco checks disponibles: al menos 10 oraciones válidas, 3 párrafos, 50 tokens y 150 bytes limpios. |
| F5, optativo | Tres checks principales disponibles: al menos 50 tokens y 150 bytes limpios. No exige párrafos para el índice. |

Son condiciones de los checks sobre el texto procesado, no una garantía basada en el número de palabras visible en un editor. Los checks eliminan cabeceras y aplican sus propios filtros.

F4 puede rechazar un texto largo si no conserva suficiente estructura. F5 puede analizar texto aplanado, pero esa cobertura no demuestra capacidad para detectar su origen.

## Opciones

```text
textector analyze (--archivo RUTA | --stdin) [--config RUTA]
                  [--json] [--detallado] [--metodo {f4,f5}] [--diagnostico]
```

| Opción | Efecto |
|---|---|
| `--archivo RUTA` | Lee un archivo UTF-8; excluyente con `--stdin`. |
| `--stdin` | Lee la entrada estándar. |
| `--json` | Devuelve el informe completo como JSON. |
| `--detallado` | En salida de texto, amplía métricas y contribuciones de cada check. |
| `--diagnostico` | Añade descripción de prosa y estructura; **solo F4**. |
| `--config RUTA` | Usa un léxico YAML-min alternativo con esquema válido. |
| `--metodo f4` | Perfil histórico predeterminado, `f4-integridad`. |
| `--metodo f5` | Perfil portable experimental, `f5-portable-v1`. |
| `--help` | Muestra la ayuda del subcomando. |

`--json` ya devuelve el informe completo; `--detallado` amplía la presentación de texto. La combinación `--metodo f5 --diagnostico` se rechaza: F5 incluye sus auxiliares en su propio informe.

## Ejemplos

```bash
# Desglose de un archivo
textector analyze --archivo texto.txt --detallado

# Informe F4 y diagnóstico descriptivo
textector analyze --archivo texto.txt --json --diagnostico

# Perfil portable experimental
textector analyze --archivo texto.txt --metodo f5 --json

# Terminal con entrada UTF-8
cat texto.txt | textector analyze --stdin --json
```

El archivo histórico `corpus/human/h01.txt`, ejecutado desde el repositorio, produce:

```text
indice_llm=15 version=f4-integridad n_disponibles=5 semillas=reales-es
```

Este ejemplo documenta la salida, no una prueba de eficacia. `version` identifica la señal; la versión del paquete se consulta en los metadatos de instalación y en [los lanzamientos](https://github.com/berniehans/textector/releases).

## Interpretar el informe

`indice_llm` representa estilo en una escala 0–100. No es probabilidad ni prueba de autoría; un valor bajo tampoco demuestra que el texto sea humano. El JSON detalla contribuciones y cobertura, SHA-256 de semillas y huella del léxico.

| Perfil | Referencia | Lectura de la banda |
|---|---|---|
| F4 | Provisional: umbral 31, margen 2 | 29–33 inclusive: abstención. Por debajo: sin señal suficiente; por encima: estilo marcado según esa referencia. |
| F5 | Desarrollo congelado: umbral 15, margen 4 | 11–19 inclusive: abstención. Las etiquetas internas fuera de banda son categorías de evaluación. |

Todas las categorías de `--diagnostico` llevan `no_concluyente=True`; el eje estructural es descriptivo y no está calibrado empíricamente. Los resultados de F3, F4 y F5 no son directamente intercambiables.

F5 pondera MATTR (0,45), densidad de clichés (0,25) y evidencia positiva de compresión (0,30), con denominador fijo 1. Ritmo y párrafos se devuelven como auxiliares fuera del índice. Si falta cualquiera de los tres checks principales, devuelve `indice_llm=null` y `predicho=abstencion`, sin redistribuir pesos.

En la evaluación externa limitada de F4 hubo **8 falsos positivos entre 90 fragmentos humanos (8,9%)** y 19 abstenciones. Los fragmentos proceden de nueve autores. F4 tampoco pudo puntuar 300 textos narrativos aplanados por falta de estructura. Véanse el [informe externo](validacion-externa-v1.md), la [validación F5](validacion-f5-portable.md) y el [cierre de investigación narrativa](plan-experimental-f5-narrativa.md).

## Errores y códigos de salida

| Situación | Salida | Código |
|---|---|---:|
| Análisis emitido, incluida abstención de F5 o por banda | Informe en stdout | 0 |
| Archivo ilegible, UTF-8 inválido, entrada vacía, léxico o semillas inválidos | Una línea en stderr; sin traceback ni volcado del texto | 1 |
| F4 no alcanza 5/5 checks | Error de cobertura; sin índice | 1 |
| F5 combinado con `--diagnostico` | Error explicando la incompatibilidad | 1 |
| Argumentos ausentes, incompatibles o desconocidos | Mensaje y ayuda de argparse | 2 |

Un código 0 indica que el programa produjo un informe; no que haya establecido autoría ni que todos los resultados sean concluyentes.

## Léxico y reproducibilidad

`--config` acepta el esquema YAML-min versión 1, listas de escalares `frase|peso|fuente`, pesos 0–100 y léxico no vacío. Solo admite `version`, `cliches` y `phrases` (legacy). Cambiar el léxico cambia la señal; registra su huella y no compares el resultado como si fuera el perfil original.

LF/CRLF y variantes Unicode NFC/NFD reciben el tratamiento definido por el núcleo. Los spans de evidencia se refieren al texto original recibido por el pipeline.

Para verificar software, usa los comandos del [README](../README.es.md#verificación). Para estudiar corpus, sigue [evaluación](calibration.md) y [procedencia](corpus.md): un conjunto ya consumido no sirve como nueva confirmación independiente.
