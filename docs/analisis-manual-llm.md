# Análisis forense manual asistido por LLM

Procedimiento para usar un LLM (como lector experto) en la parte **cualitativa**
de la detección de texto IA, complementando `textector` y los detectores web.
Este documento es la versión de proyecto de la skill homónima del agente.

## Regla de oro

> Un LLM puede describir **señales de estilo** con precisión; no puede
> adjudicar autoría. Su salida se reporta como *evidencia descriptiva*, nunca
> como veredicto. Un texto con señales fuertes puede ser humano; uno sin
> señales puede ser IA editada.

## Cuándo usarlo

- Cuando `textector` devuelve **abstención** (`18 ≤ indice < 26`).
- Cuando los detectores web dicen «humano» con 0 % y el texto *suena* a plantilla.
- Cuando el flujo real es **híbrido** (persona estructura, IA redacta): el caso
  donde todos los detectores de superficie fallan.

## Procedimiento (4 pasos)

### 1. Inventario antes de leer

Registra: longitud, nº de secciones/capítulos, proporción de diálogo (línea que
empieza por «—»), presencia de cabeceras numeradas (`S01`, `I.`, `1.`), y si el
texto tiene marcas de superficie (erratas, inconsistencias, cambios de registro).
Esto separa **estructura** de **prosa** antes de opinar sobre autoría.

### 2. Barrido de señales de prosa (checklist)

Para cada señal, cita **una evidencia literal** (frase corta) o marca «ausente»:

| # | Señal | Qué buscar en español |
|---|---|---|
| 1 | Perífrasis «de quien» | relativa de manual: «con esa calma *de quien* ya lo ha visto todo» |
| 2 | Díadas antiteticéticas pulidas | «antiguo *y* nuevo *a la vez*», «una tristeza luminosa» |
| 3 | Listas 3-en-3 | tres sustantivos, tres infinitivos, tres subordinadas seguidas |
| 4 | Simetría de diálogo | réplicas cortas que responden exactamente; sin solapamientos ni interrupciones |
| 5 | Uniformidad de párrafo | longitudes de párrafo casi iguales; beats descripción→diálogo→reacción→cierre |
| 6 | Bloque expositivo de mundo | *worldbuilding* suave insertado sin fricción (tecnología, medicina, leyes) |
| 7 | Léxico de cierre reflexivo | «Al final…», «Con el tiempo…», aforismo final que resume una tesis |
| 8 | Superficie impecable | cero erratas, puntuación de raya perfecta, registro constante |
| 9 | Autoreferencia temática | ficción sobre IA escrita con vocabulario técnico exacto |
| 10 | Ausencia de idiolecto | no hay giros locales, ni obsesiones, ni humor irregular |

### 3. Contraste estructural

- ¿Las escenas tienen largos dispares o clonados?
- ¿Los títulos/cabeceras son de trabajo («S01 — …») o de plantilla («Introducción», «Conclusión»)?
- ¿El texto cambia de registro entre secciones (humano) o se mantiene plano (plantilla)?
- **Híbrido típico**: cabeceras propias + prosa impecable y homogénea.

### 4. Contraste externo y cierre

- Corre `textector` (`--diagnostico`) y, si aporta, un detector web.
- Reporta en tres bloques: **evidencia** (citas), **señales ausentes**, y
  **veredicto cualitativo con confianza** (baja/media/alta) + advertencia.
- Si el usuario explica el flujo de producción (p. ej. «yo estructuro, la IA
  redacta»), **eso prevalece** sobre cualquier score: los detectores no ven el
  proceso, solo la superficie.

## Plantilla de prompt para el LLM analista

```text
Actúa como analista forense de estilo en español. NO emitas un veredicto de
autoría: describe señales.

1. Inventario: longitud, nº de secciones, % de diálogo, cabeceras, marcas de
   superficie.
2. Para cada señal de la lista (perífrasis «de quien», díadas pulidas, listas
   3-en-3, simetría de diálogo, uniformidad de párrafo, bloque expositivo,
   cierre aforístico, superficie impecable, autoreferencia temática, ausencia
   de idiolecto): cita UNA evidencia literal o marca «ausente».
3. Separa explícitamente ESTRUCTURA (esqueleto, títulos, escenas) de PROSA
   (frases, ritmo, léxico).
4. Cierra con: confianza (baja/media/alta), qué NO se puede concluir, y una
   advertencia de no-uso probatorio.

Reglas: no inventes citas; si no hay evidencia, dilo; no uses el estilo como
prueba de autoría; señala si el patrón es compatible con «estructura humana +
redacción IA».
```

## Anti-sesgos

- No leas el veredicto de un detector **antes** de hacer el barrido (ancla).
- No confundas «me gusta / no me gusta» con señal.
- No conviertas «pulido» en «IA»: hay escritores excelentes.
- Con texto híbrido, el score bajo **no** exculpa: la prosa IA guiada por un
  esqueleto humano es exactamente el punto ciego de los detectores.

## Caso de referencia (2026-10, anonimizado)

Texto narrativo en español de extensión media, dividido en una decena de
escenas con cabeceras numeradas:

- `textector` → índice por debajo del umbral (banda de abstención).
- Detector web gratuito → 0 % de señal, escaneado por tramos por el límite de
  caracteres.
- Barrido manual → mayoría de las señales presentes con evidencia (listas
  3-en-3, perífrasis de manual, díadas pulidas, simetría de diálogo, bloques
  expositivos).

El flujo de producción declarado por el autor era **estructura propia +
redacción IA**. Conclusión registrada: los detectores de superficie no separan
ese flujo; el valor del análisis manual es **describir** qué parte es plantilla
y qué parte es voz.
