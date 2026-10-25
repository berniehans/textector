# Guía de uso

Requiere Python >=3.11. Runtime sin dependencias externas. Desde el checkout:

```bash
uv run python -B tools/cli.py analyze --archivo texto.txt
uv run python -B tools/cli.py analyze --archivo texto.txt --json --diagnostico
uv run python -B tools/cli.py analyze --stdin --detallado
```

Tras instalar el wheel: `textector analyze --archivo texto.txt --json`.
No requiere el checkout ni el corpus completo: los recursos están incluidos.

## Opciones

| Opción | Efecto |
|---|---|
| `--archivo RUTA` | Lee UTF-8; excluyente con stdin |
| `--stdin` | Lee la entrada estándar |
| `--json` | Informe completo serializable |
| `--detallado` | Contribución, peso, normalizado y métricas de cada check |
| `--diagnostico` | Añade descripción de prosa y estructura |
| `--config RUTA` | Léxico YAML-min alternativo, con esquema válido |
| `--metodo f4` | Perfil histórico (predeterminado) |
| `--metodo f5` | Perfil portable experimental, con abstención explícita |

## Interpretación

`indice_llm` es un índice de estilo 0..100, no probabilidad ni prueba de autoría.
`version=f4-integridad` conserva la señal histórica. Para el perfil portable experimental, elija `--metodo f5`; el CLI sigue usando F4 si no se especifica.
El JSON incluye SHA256 de las semillas y una huella del contenido del léxico.

F5 pondera MATTR (0,45), densidad de clichés (0,25) y evidencia positiva de
compresión (0,30), con denominador fijo 1. Los checks de ritmo y párrafos se
devuelven como auxiliares fuera del índice. Si cualquiera de los tres checks
principales resulta insuficiente, F5 no renormaliza y se abstiene.

La referencia provisional del diagnóstico es umbral 31/margen 2: banda inclusiva
29..33. Menor que 29 significa sin señal suficiente; mayor que 33 indica estilo
marcado bajo esa referencia. Ningún caso determina autoría. Todas las categorías
son `no_concluyente=True`; el eje estructural no está calibrado empíricamente.
F4 requiere un corpus y holdout nuevos para validación independiente.

## Errores

Los errores de lectura/UTF-8, entrada vacía, falta de cobertura de alguno de los
cinco checks, YAML/esquema inválido o semillas ausentes/vacías se reportan en una
línea por stderr, exit 1, sin índice ni traceback. Errores de argumentos los
gestiona argparse con exit 2 y su ayuda de uso.

El esquema exige versión 1, listas de escalares `frase|peso|fuente`, pesos 0..100
y léxico no vacío. Solo admite `version`, `cliches` y `phrases` (legacy).
Saltos CRLF y LF y variantes Unicode NFC/NFD se procesan de forma equivalente.
Los spans de evidencia conservan los offsets del texto original.

Ver [evaluación](calibration.md), [checks](checks.md) e [integridad](integridad-f4.md).
