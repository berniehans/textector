# textector

CLI en español que calcula un **índice heurístico explicable de 0 a 100**
(`indice_llm`) a partir de señales de estilo. Es un **pre-filtro para
revisión humana**: no es una probabilidad ni una prueba de autoría. Un índice
bajo tampoco demuestra que un texto sea humano.

## Estado actual

Versión del paquete **0.3.0**; F4 **`f4-integridad`** se mantiene por compatibilidad y F5 **`f5-portable-v1`** es un perfil portable experimental. Python
3.11 o posterior, biblioteca estándar en ejecución y sin llamadas de red.

F4 es el perfil predeterminado y usa cinco checks. F5 (`--metodo f5`) usa tres
checks léxicos con pesos fijos, se abstiene cuando falta cualquiera y deja el
ritmo y los párrafos fuera del índice. No inventa segmentación cuando el texto
está aplanado. Su validación independiente está documentada en
[`docs/validacion-f5-portable.md`](docs/validacion-f5-portable.md).

La reparación de integridad corrige recursos del wheel, segmentación, Unicode,
entradas insuficientes, configuración, estructura, hashes y evaluación por folds.
Los pesos y las transformaciones de los cinco checks se conservan. Las semillas
históricas mantienen sus bytes; su composición exacta figura en
[`corpus/seeds/manifest.json`](corpus/seeds/manifest.json).

**f4 tiene una evaluación externa limitada**, documentada en
[`docs/validacion-externa-v1.md`](docs/validacion-externa-v1.md): 8 falsos positivos
en 90 fragmentos humanos y 190 señales IA en 200 relatos infantiles publicados.
Otros 300 textos IA quedan sin puntuar por su formato. Esto no valida un detector
general de autoría. Los índices no son comparables
directamente con f3: corregir el preprocesado cambia la señal. El diagnóstico usa
una referencia **provisional** de umbral 31 y margen 2, banda inclusiva 29..33.
Todas las categorías llevan `no_concluyente=True`. Esta referencia histórica
no se presenta como una calibración general validada para f4. El estado interno
`provisional-sin-validacion-f4` se conserva en el código congelado: la evaluación
externa limitada no habilita uso probatorio ni valida generalización.

La auditoría detectó filtración de semillas y agregación incorrecta de tasas en
la CV anterior. Sus números se conservan como registro afectado en
[`docs/historico/calibracion-f3.md`](docs/historico/calibracion-f3.md).
Nueva evidencia de generalización exige **corpus y holdout nuevos**, según el
alcance adoptado en F8; el holdout histórico no se evalúa por defecto.

## Uso desde el repositorio

```bash
uv run python -B tools/cli.py analyze --archivo texto.txt --detallado
uv run python -B tools/cli.py analyze --archivo texto.txt --metodo f5 --json
uv run python -B tools/cli.py analyze --stdin --json --diagnostico
```

Solo se admite una fuente: `--archivo` UTF-8 o `--stdin`. El JSON incluye versión,
contribuciones, cobertura, huellas de semillas y del léxico; `--diagnostico` añade
la lectura descriptiva de prosa y estructura. `--config` permite un léxico
alternativo válido; cambiarlo también cambia la señal.

Los errores de lectura, entrada vacía/insuficiente, configuración o semillas se
reportan en una línea por stderr, exit 1, sin traceback ni volcado del texto.
F4 exige sus cinco checks para emitir un índice. F5 se elige explícitamente y
exige MATTR, densidad léxica y compresión; si falta cualquiera, entrega
`indice_llm=null` y `predicho=abstencion`.

## Paquete instalable

```bash
uv build --wheel
python -m pip install dist/textector-0.3.0-py3-none-any.whl
textector analyze --archivo texto.txt --json
```

El wheel incluye el léxico y ambas semillas como recursos del paquete. Funciona
fuera del checkout; el corpus completo solo es necesario para la evaluación.

## Verificación

```bash
uv run python -B -m unittest discover -s tests -p "test_*.py" -v
uv build --wheel
uv run python -B tests/verify_wheel.py dist/textector-0.3.0-py3-none-any.whl
uv run python -B -m tools.calibrate
```

El último comando evalúa únicamente TRAIN: reconstruye las semillas sin el grupo
excluido, recalcula los índices por fold y agrega predicciones fuera de muestra.
Reporta matriz, tasas condicionadas a no abstención y cobertura por clase. No
actualiza automáticamente los parámetros del CLI. Ver
[`docs/calibration.md`](docs/calibration.md).

## Estructura y documentación

El historial de cambios está en [`CHANGELOG.md`](CHANGELOG.md).

| Ruta | Contenido |
|---|---|
| `tools/textector_core.py` | Normalización, tokens y spans sobre el original |
| `tools/checks/`, `tools/scoring.py` | Cinco checks, pesos y contribuciones |
| `tools/pipeline.py` | Pipeline común a CLI y evaluación |
| `tools/decision.py` | Regla única de abstención, referencia provisional |
| `tools/estructura.py`, `tools/diagnostico.py` | Estructura y lectura descriptiva |
| `tools/resources.py` | Recursos del checkout y del paquete |
| `tools/calibrate.py` | Integridad del corpus y LOGO-CV |
| `tools/f5.py`, `tools/calibrate_f5.py` | Perfil portable y calibración solo en desarrollo |
| [`docs/guia-uso.md`](docs/guia-uso.md) | Comandos, errores e interpretación |
| [`docs/checks.md`](docs/checks.md) | Señales y constantes |
| [`docs/corpus.md`](docs/corpus.md) | Procedencia, hashes y semillas |
| [`docs/diagnostico-hibrido.md`](docs/diagnostico-hibrido.md) | Dos ejes y límites |
| [`docs/integridad-f4.md`](docs/integridad-f4.md) | Cambios y alcance de la reparación |
| [`NOTICE`](NOTICE) | Atribuciones y procedencia temática |

Licencia MIT: [`LICENSE`](LICENSE). Las licencias de los corpus de terceros
se identifican en el manifiesto y NOTICE.
