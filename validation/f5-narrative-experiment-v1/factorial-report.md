# Informe experimental F5 para narración en español

**Protocolo:** `f5-narrative-experiment-v1`

**Corrida:** 2026-10-25T21:42:22.800740+00:00

**Estado:** development_experiment_complete_not_confirmatory

**Umbral/margen:** 15/4 (congelados)

**Conjunto reservado:** no leído ni puntuado.

## Pregunta, hipótesis y contrahipótesis

- **H0 global:** al menos una puerta de promoción falla en la población objetivo.
- **H1 global:** FP humana ≤5%, cobertura humana ≥80% y detección IA ≥80% en cada fuente, con límites unilaterales del 95% que también cumplen las puertas.
- **H0 de señal:** al menos una fuente no mejora ≥5 puntos porcentuales frente a B0. **H1:** cada fuente mejora ≥5 pp.
- **H0 de interacción:** los efectos L2, C2-v2 y M100 son aditivos en la escala de proporciones. **H1:** existe al menos una interacción factorial distinta de cero.
- La interpretación de detección es la del prefiltro experimental; no prueba autoría individual.

## Método ejecutado

Se puntuaron 1912 documentos de desarrollo para la referencia B0/F4 y 1896 en la matriz 2×2×2. Se retiraron 16 filas IA correspondientes a 8 prompts usados por C2-v2. Se compararon B0, L2, C2-v2, M100 con fallback M50 entre 50–99 tokens y todas sus combinaciones. C2 usa ocho documentos por clase, 64 pares emparejados por bytes y mediana; 1024 bytes es el análisis principal, 512/1280 son sensibilidad.
La auditoría lingüística manual comprende 404 filas: 157 español, 239 inglés y 8 mixtas. El panel IA español contiene 157 filas y 68 prompts; las filas sin etiqueta manual se presentan solo de forma descriptiva.

## Resultados por perfil

Detección IA en español se pondera por el diseño de auditoría y se define sobre todos los casos IA, incluidas abstenciones. FP y cobertura humana usan todos los 120 textos humanos.

| Perfil | L2 | C2-v2 | M100 | FP humana | Cobertura humana | Detección IA ES ponderada | Fuentes ≥80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| P000 | No | No | No | 0.0% | 92.5% | 0.3% | 0/8 |
| P001 | No | No | Sí | 32.5% | 34.2% | 93.2% | 7/8 |
| P010 | No | Sí | No | 0.0% | 92.5% | 1.5% | 0/8 |
| P011 | No | Sí | Sí | 32.5% | 34.2% | 93.3% | 7/8 |
| P100 | Sí | No | No | 2.5% | 88.3% | 15.2% | 0/8 |
| P101 | Sí | No | Sí | 37.5% | 39.2% | 93.8% | 7/8 |
| P110 | Sí | Sí | No | 2.5% | 88.3% | 17.8% | 0/8 |
| P111 | Sí | Sí | Sí | 37.5% | 39.2% | 93.8% | 7/8 |

### Detección por fuente, porcentaje

| Perfil | Arcee Blitz | Mistral Nemo | Gemma SPPO | Llama 3.1 | Gemma Ataraxy | Hermes 3 | Gemma 2 9B | Mistral Small |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P000 | 1.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.6% | 0.0% |
| P001 | 98.4% | 95.7% | 84.5% | 100.0% | 71.2% | 100.0% | 99.6% | 97.7% |
| P010 | 1.6% | 0.0% | 0.0% | 0.0% | 0.0% | 8.5% | 0.6% | 0.0% |
| P011 | 98.4% | 95.7% | 85.4% | 100.0% | 71.2% | 100.0% | 99.6% | 97.7% |
| P100 | 19.2% | 0.0% | 0.0% | 30.0% | 1.9% | 21.9% | 18.8% | 19.7% |
| P101 | 100.0% | 100.0% | 85.9% | 100.0% | 71.2% | 100.0% | 99.6% | 97.7% |
| P110 | 19.2% | 0.0% | 0.0% | 30.0% | 1.9% | 21.9% | 36.4% | 19.7% |
| P111 | 100.0% | 100.0% | 86.3% | 100.0% | 71.2% | 100.0% | 99.6% | 97.7% |

El orden de las ocho columnas sigue las fuentes del manifiesto: Arcee, Nemo, SPPO, Llama, Ataraxy, Hermes, Gemma, Mistral S.

## Contrastes e hipótesis de mejora

| Perfil vs B0 | Mínimo delta entre fuentes | Máximo delta | ≥5 pp en todas las fuentes |
|---|---:|---:|---:|
| P001 | 71.2% | 100.0% | Sí |
| P010 | 0.0% | 8.5% | No |
| P011 | 71.2% | 100.0% | Sí |
| P100 | 0.0% | 30.0% | No |
| P101 | 71.2% | 100.0% | Sí |
| P110 | 0.0% | 35.8% | No |
| P111 | 71.2% | 100.0% | Sí |

### Efectos principales e interacciones factoriales

La tabla incluye los efectos principales (un factor) y los contrastes de interacción (dos o tres factores); estos últimos evalúan H0/H1 de aditividad. Se calcularon como contraste factorial de detección, con bootstrap por prompt IA y por autor humano (2000 réplicas). Son intervalos bilaterales exploratorios; la auditoría estratificada y el bajo número de conglomerados impiden interpretarlos como confirmación.

| Efecto/contraste IA español ponderado | Estimación (pp) | IC exploratorio 95% (pp) |
|---|---:|---:|
| L2 | 8.08 | 4.09 a 12.43 |
| C2-v2 | 0.99 | 0.05 a 2.46 |
| M100-fallback50 | 84.79 | 77.16 a 91.28 |
| L2 × C2-v2 | 0.31 | -0.77 a 1.59 |
| L2 × M100-fallback50 | -7.51 | -11.80 a -3.54 |
| C2-v2 × M100-fallback50 | -0.90 | -2.35 a 0.05 |
| L2 × C2-v2 × M100-fallback50 | -0.35 | -1.64 a 0.71 |

## Controles y puertas

B0 completo: detección IA descriptiva 2.0%, FP humana 0.0%, cobertura humana 92.5%.
F4 completo: detección IA descriptiva 63.7%, FP humana 9.2%, cobertura humana 91.7%.

Ningún perfil pasa todas las puertas en esta pantalla de desarrollo. Incluso donde las tasas puntuales humanas pasan, ninguna opción alcanza ≥80% de detección en las ocho fuentes. Los límites de confianza para promoción no se consideran aprobados: el resultado correcto es **datos insuficientes para promoción**, no selección de un ganador.

## Sensibilidad C2 y conclusión

- 512 bytes: delta medio de q frente a 1024 = -0.0045; detección española ponderada con C2 = 1.5%.
- 1280 bytes: delta medio de q frente a 1024 = 0.0017; detección española ponderada con C2 = 2.8%.

La evidencia de desarrollo no justifica promover F5 ni cambiar umbral/margen. M100 aporta detección pero falla claramente las puertas humanas; L2 respeta las puertas humanas por puntos en P100/P110 pero no resuelve varias fuentes; C2-v2 tiene un efecto pequeño. Mantener B0 congelado y diseñar confirmación independiente, con más autores/prompts y auditoría lingüística suficiente. No usar este análisis para calibrar el umbral.

## Reproducibilidad e integridad

- Reserva leída: `False`.
- Umbral y margen retocados: `False`.
- SHA-256 del lock C2: `775345e347d6f168a3638458cec64d12c0543ee993af1f2e4f3016b0ed4a1a35`.
- SHA-256 del manifiesto factorial: `a729ec52da37a1e3ac86d2db08de81de817c2a96108723470f9f501edad50b5e`.
- SHA-256 del código del runner: `b2dde5c1e30e70d6c30f2a4bc985671bbf7f293cf88632a51454cb409896a1d2`.
- SHA-256 de resultados completos: `91d1dd1cb565cc7f7a77c2d31728683054779ca88748e55c0924bb99157c6a60`.
- SHA-256 de interacciones: `e4b4668420917c45f987a7f2f24607b1be486a776d69d7a5286d5d56c1646b18`.
- Artefactos: `factorial-results.json` (por caso y resumen), `factorial-case-scores.jsonl`, `factorial-interactions.json`, manifiesto y lock bajo `validation/f5-narrative-experiment-v1/`.
