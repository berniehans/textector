# Revisión de preparación de lanzamiento — textector 0.3.1

**Fecha:** 25 de octubre de 2026

**Alcance:** afirmaciones públicas, guía, ayuda del CLI y metadatos del paquete.

**Resultado:** **apto solo como prefiltro heurístico experimental con revisión humana**; no apto para presentar como detector probado ni para decisiones automáticas de autoría.

## Decisión

La publicación puede describir `textector` como una herramienta local y explicable que calcula señales de estilo para apoyar una revisión humana. Debe indicar que sus índices no son probabilidades y no establecen quién escribió el texto.

La evaluación externa disponible para el perfil predeterminado F4 registró **8 falsos positivos en 90 fragmentos humanos (8,9%)**. Los fragmentos corresponden a nueve grupos de autor, por lo que 90 no equivale a 90 autores independientes. F4 produjo señal en **190 de 200** relatos infantiles publicados de Gemini y se abstuvo en **300 de 300** textos de narrativa española aplanados por insuficiencia de formato. Son paneles de géneros y formatos distintos, no una estimación representativa de uso general. La evaluación tampoco autoriza decisiones de alto impacto ni conclusiones por persona. Véase [la evaluación externa](validacion-externa-v1.md).

F4 mantiene la referencia provisional **31/2** (banda de abstención inclusiva 29–33), y las categorías del diagnóstico llevan `no_concluyente=True`. Ese estado debe seguir visible junto con el resultado. El perfil F5 continúa disponible solo por selección explícita, experimental y congelado; la investigación narrativa de F5 se cerró sin promoción. Véase [el informe de cierre](plan-experimental-f5-narrativa.md).

## Revisión realizada

- README y guía de uso: presentan la herramienta como prefiltro humano, declaran límites y enlazan las evaluaciones.
- Ayuda del CLI: se reforzó la advertencia de revisión humana y evaluación externa limitada.
- Metadatos: se retiraron las palabras clave `forense` y `deteccion-ia`; `tools.__version__` y el proyecto quedaron alineados en `0.3.1`.
- F5: queda optativo y experimental; no se alteraron los pesos, el perfil, el umbral 15 ni el margen 4.
- Scoring F4, regla provisional 31/2 y nombres de campos/salidas: no se cambiaron.

## Condiciones antes de anunciar un lanzamiento público

1. La matriz local de Windows pasó en Python 3.11 y 3.13: 159 pruebas por versión, smoke del CLI, wheel construido e instalado/verificado fuera del checkout. Falta que el workflow remoto ejecute Linux en ambas versiones.
2. Confirmar que el paquete que se publique contiene los recursos F4/F5 y que la versión del artefacto es 0.3.1.
3. Mantener en la página de distribución el alcance de prefiltro y los límites de evaluación descritos aquí; no usar frases como “detecta autoría” o “identifica texto IA con fiabilidad”.
4. Si se modifica F4 tras revisar esta evidencia, asignar una versión de señal nueva y validar con datos nuevos; no recalibrar mirando `external-v1` ni reabrir reservas consumidas.

## Estado

**Preparación documental y validación local: completadas.**

**Lanzamiento del artefacto: pendiente del CI remoto Linux y la publicación en GitHub.**

**Uso permitido por la evidencia: apoyo experimental a revisión humana.**
