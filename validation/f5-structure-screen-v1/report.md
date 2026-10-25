# Resultado del cribado estructural F5 v1

Estado: `development_screen_not_confirmatory`. Reserva leída: `False`. Umbral/margen modificados: `False`.
Casos elegibles: 277; humanos: 120 en 15 autores; IA española manual: 157 en 68 prompts y 8 fuentes.

## Resultados OOF anidados

| Modelo | FP humano | Salida humana del clasificador* | Detección IA ponderada | AUC OOF |
|---|---:|---:|---:|---:|
| M0_B0 | 2.5% | 100.0% | 13.7% | 0.780 |
| M1_B0_length | 4.2% | 100.0% | 14.9% | 0.795 |
| M2_B0_length_structure | 4.2% | 100.0% | 79.1% | 0.982 |

\* La regresión logística siempre emite una etiqueta, así que 100% es cobertura del clasificador diagnóstico por construcción; **no** es cobertura F5. En estos 120 humanos, F5/B0 conserva su decisión congelada y obtiene 0% FP y 92,5% de cobertura. El umbral operativo del clasificador experimental se seleccionó dentro de cada entrenamiento para limitar FP, y no cambia el 15/4 de F5.

| Checkpoint IA | M1 detección | M2 detección | Diferencia | N / prompts |
|---|---:|---:|---:|---:|
| Arcee Blitz | 22.1% | 45.2% | +23.1 pp | 21 / 18 |
| Mistral Nemo | 7.3% | 79.0% | +71.7 pp | 17 / 12 |
| Gemma SPPO | 0.0% | 86.8% | +86.8 pp | 19 / 14 |
| Llama 3.1 | 40.5% | 73.2% | +32.7 pp | 21 / 18 |
| Gemma Ataraxy | 1.9% | 80.0% | +78.0 pp | 19 / 14 |
| Hermes 3 | 23.4% | 89.8% | +66.4 pp | 20 / 17 |
| Gemma 2 9B | 9.9% | 100.0% | +90.1 pp | 20 / 17 |
| Mistral Small | 4.5% | 78.9% | +74.4 pp | 20 / 15 |

Delta M2−M1 en detección ponderada: **64.17 pp**; fuentes que mejoran ≥5 pp: **8/8**.

## Veredicto

`candidate_for_independent_confirmation` **por criterios puntuales de cribado solamente**. La incertidumbre humana no certifica la puerta: el bootstrap agrupado exploratorio deja límite superior de FP de 7,5%, por encima del máximo 5%; con 15 autores, no es una prueba confirmatoria. El candidato requiere una nueva evaluación independiente antes de cualquier decisión de producto.

## Sensibilidad secundaria: checkpoint fuera de entrenamiento

Después del análisis primario, a petición de la revisión Astra se dejó fuera del entrenamiento un checkpoint a la vez y se eligió el corte con OOF agrupado del resto. El promedio macro de detección en el checkpoint excluido fue 90,9% con M2 frente a 22,6% con M1; los ocho checkpoints mejoraron al menos 5 pp. El desglose y hashes están en `source-holdout-sensitivity.json`.

Esta sensibilidad **no es una prueba de fuente completamente nueva**: 18 de los 68 prompts aparecen en más de un checkpoint (máximo siete). Cuando se excluye un checkpoint, algunos de sus prompts siguen representados mediante otras generaciones en entrenamiento. Tampoco hay un conjunto humano externo nuevo. Interpretarla como señal de transferencia entre checkpoints de este banco, no como confirmación externa.

El resultado es un cribado de desarrollo; no autoriza promoción, no prueba imposibilidad general y no cambia el corte F5 15/4.
Los límites bootstrap por grupo se guardan en `results.json` y son descriptivos, no certificados.

## Integridad

- SHA-256 protocolo: `16b9070282e69be6a01dca864df92b5f0e476cd1880f5cac7cb404262f2514e9`
- SHA-256 manifiesto: `a729ec52da37a1e3ac86d2db08de81de817c2a96108723470f9f501edad50b5e`
- SHA-256 etiquetas: `cc058127233d0ed8b41d7fe45a003bd5ba8d15e178e072c8a3dbf2890d6f6e88`
- SHA-256 runner: `3e78e49334c136de6b4e116c12a44e19fc0370cdf98fa06b4756c17016c8b780`
- Umbral y margen F5 preservados: `15/4`
