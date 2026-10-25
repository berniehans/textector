# Diagnóstico descriptivo de dos ejes

La prosa (`indice_llm`) y la estructura se presentan por separado, sin fusionarlas
en un número nuevo. Ninguna categoría es concluyente ni prueba autoría.

## Referencia provisional compartida

`tools/decision.py`: umbral 31 y margen 2; banda inclusiva **29..33**.
Se conserva como referencia histórica, **sin validación independiente de f4**.

| Prosa | Estructura | Categoría |
|---|---|---|
| >33 | regular >=60 | `plantilla_prosa_y_estructura` |
| >33 | irregular <=40 | `probable_hibrido_estructura_propia_prosa_ia` |
| 29..33 | cualquiera | `prosa_no_concluyente` |
| <29 | irregular | `sin_senal_suficiente` |
| <29 | regular | `estructura_regular_prosa_no_marcada` |
| Fuera de banda | intermedia o insuficiente | `prosa_no_concluyente` |

**Todas devuelven `no_concluyente=True`.** Los nombres de categoría conservan
compatibilidad de identificación; son patrones descriptivos, no evidencia del
proceso de escritura. «Probable híbrido» es un nombre histórico, no una
probabilidad calibrada. La nota explica esa limitación.

## Estructura

Exige al menos dos secciones con contenido. Reconoce `S01`, `S02`..., con hasta
tres `#`, con/sin título y separadores `—`, `–`, `:` o `-`.
Una sola sección o secciones vacías producen `insufficient=True`, valor 0.

La regularidad es la media de transformaciones decrecientes de CV de tamaños
de sección ([0.05,0.60]), número de párrafos ([0.15,0.80]) y proporción de diálogo
([0.10,0.50]). Ausencia de diálogo usa un componente neutral de 0.5. Bonus 0.05
solo si los **números reales** de cabecera son consecutivos desde 1; el título
no interviene. Resultado acotado a [0,1], valor redondeado 0..100.

Etiquetas: regular >=60, irregular <=40, intermedia entre ambas. Esas fronteras
son decisiones de diseño sin calibración empírica. Una estructura regular puede
ser un formato de trabajo humano. Los otros estilos de cabecera no se detectan.

`--diagnostico` añade este bloque al JSON o a la salida de lectura humana.
