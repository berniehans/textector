# Revisión de lanzamiento — textector 0.3.1

**Fecha de publicación:** 25 de octubre de 2026. **Estado documental actualizado:** 26 de octubre de 2026.

**Resultado:** publicado como **prefiltro heurístico experimental con revisión humana**. El índice no establece autoría ni constituye una probabilidad.

## Alcance de la decisión

La publicación presenta una herramienta local y explicable que calcula señales de estilo para apoyar revisión humana. Los resultados de software y de corpus tienen alcances distintos.

La evaluación externa F4 registró **8 falsos positivos en 90 fragmentos humanos (8,9%)**, procedentes de nueve grupos de autor. F4 produjo señal en **190 de 200** cuentos infantiles publicados atribuidos a Gemini y se abstuvo en **300 de 300** textos de narrativa española aplanados por insuficiencia de formato. Los paneles difieren en género, longitud y formato. Véase [la evaluación externa](validacion-externa-v1.md).

F4 conserva la referencia provisional **31/2**, banda inclusiva 29–33. Las categorías del diagnóstico llevan `no_concluyente=True`. F5 sigue disponible por selección explícita, experimental y congelado en **15/4**; la investigación narrativa se cerró sin promoción. Véase [el informe de cierre](plan-experimental-f5-narrativa.md).

## Comprobaciones completadas

| Comprobación | Resultado |
|---|---|
| Windows local, Python 3.11 y 3.13 | 159 pruebas por versión, CLI y wheel correctos. |
| GitHub Actions: Ubuntu/Windows × Python 3.11/3.13 | Cuatro trabajos completados correctamente: pruebas, CLI, construcción e instalación independiente del wheel. |
| Recursos del wheel | Léxico, configuración F5 y ambas semillas presentes; comportamiento F4/F5 y paridad verificados. |
| Metadatos | Versión del paquete 0.3.1 y descripción alineada con prefiltro humano. |
| Documentación pública | Evidencia limitada F4 y condición experimental F5 visibles. |
| Publicación | PR fusionado, etiqueta v0.3.1 y release pública con wheel adjunto. |

[CI del PR de lanzamiento](https://github.com/berniehans/textector/actions/runs/40247018585) · [PR #2 fusionado](https://github.com/berniehans/textector/pull/2) · [Release 0.3.1](https://github.com/berniehans/textector/releases/tag/v0.3.1).

## Artefacto publicado

- Commit de lanzamiento: `e84aadefbe1f9f31bd27a83a800d78b8c6e10a61`.
- Etiqueta: `v0.3.1`.
- Wheel: `textector-0.3.1-py3-none-any.whl`, 135.974 bytes.
- SHA-256 del wheel: `71524dd4733892d9219e133f0df154792123de7907e2dc8eb73b78d266d13db2`.
- Distribución: GitHub Releases. No se publicó en PyPI.

## Condiciones para una evolución futura

Cambiar F4 o F5 requiere identificar una nueva versión de señal y definir una evaluación independiente antes de puntuar. No se recalibra mirando `external-v1` ni se reabren reservas consumidas como si fueran confirmación nueva. Los informes históricos se conservan con su procedencia y sus limitaciones.

La actualización de presentación del 26 de octubre añade README bilingüe, índice documental y guías revisadas. Es documentación posterior al lanzamiento: no modifica el artefacto 0.3.1 publicado ni los pesos, el preprocesado o los umbrales de sus perfiles.
