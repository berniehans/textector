# Documentación de textector

[README en español](../README.es.md) · [English overview](../README.md) · [Versión 0.3.1](https://github.com/berniehans/textector/releases/tag/v0.3.1)

textector se distribuye como un prefiltro heurístico experimental para revisión humana. La versión del paquete es **0.3.1**; F4 es el perfil predeterminado y F5 continúa optativo y congelado.

## Empezar y comprender el informe

| Documento | Pregunta que resuelve |
|---|---|
| [Guía de uso](guia-uso.md) | ¿Cómo instalo, ejecuto e interpreto la CLI? |
| [Arquitectura](arquitectura.md) | ¿Cómo se conectan entradas, recursos, checks y salidas? |
| [Referencia de checks F4](checks.md) | ¿Qué mide cada señal y cuáles son sus constantes? |
| [Diagnóstico híbrido](diagnostico-hibrido.md) | ¿Cómo se describen prosa y estructura sin concluir autoría? |
| [Corpus y semillas](corpus.md) | ¿De dónde provienen los datos y cómo se identifican? |
| [Cambios](../CHANGELOG.md) | ¿Qué cambió entre versiones? |
| [Licencias y atribuciones](../NOTICE) | ¿Qué procedencias y restricciones de terceros se conservan? |

## Evidencia vigente y alcance de publicación

| Documento | Alcance |
|---|---|
| [Revisión del lanzamiento 0.3.1](revision-lanzamiento-0.3.1.md) | Decisión de publicación, CI, wheel y límites públicos. |
| [Evaluación externa F4](validacion-externa-v1.md) | Paneles humanos pre-2020 y generaciones publicadas, con falsos positivos y abstenciones. |
| [Evaluación interna F4](calibration.md) | Reconstrucción de semillas por grupo y tasas con denominadores explícitos; exploratoria. |
| [Reparación de integridad F4](integridad-f4.md) | Unicode, segmentación, cobertura, recursos y correcciones de evaluación. |
| [Perfil portable F5](validacion-f5-portable.md) | Definición y evidencia histórica del perfil optativo; no demuestra generalización. |

Las pruebas de software comprueban implementación y empaquetado. Las evaluaciones de corpus deben leerse junto con su procedencia, cobertura, unidad de independencia y factores de confusión.

## Investigación narrativa F5: cerrada sin promoción

Estos documentos conservan el recorrido experimental. Ninguno autoriza por sí solo a cambiar el perfil publicado ni a reabrir reservas para ajustar resultados.

| Documento | Contenido |
|---|---|
| [Plan y cierre experimental](plan-experimental-f5-narrativa.md) | Hipótesis, controles, puertas y decisión de no promoción. |
| [Auditoría de corpus confirmatorio](auditoria-busqueda-corpus-confirmatorio-f5.md) | Búsqueda final y descarte de fuentes que no cumplen las condiciones. |
| [Auditoría previa de fuentes](auditoria-pre-f5-fuentes-externas.md) | Elegibilidad, separación y límites de corpus candidatos. |
| [Auditoría de metadatos humanos](auditoria-metadatos-humanos-f5.md) | Autoría, época y grupos de procedencia para desarrollo. |
| [Cribado estructural](f5-structure-screen-v1.md) | Exploración de señales estructurales en desarrollo. |
| [Investigación bibliográfica](investigacion-web-corpus-senales-f5.md) | Indicios y fuentes que motivaron los experimentos. |
| [Informe factorial de desarrollo](../validation/f5-narrative-experiment-v1/factorial-report.md) | Resultados de variantes frente a las puertas declaradas. |

## Antecedentes y referencias técnicas

- [Metodología original](methodology.md): antecedentes de las señales; leer sus referencias históricas con la reparación F4.
- [Calibración F3 archivada](historico/calibracion-f3.md): registro afectado por filtración y agregación; no es evidencia independiente vigente.
- [Auditoría de zippy](audit_zippy.md), [auditoría de AI Fingerprint](audit_aifingerprint.md) y [cotejo de AIStoryHub](cotejo-aistoryhub.md): procedencia y decisiones técnicas.
- [Análisis manual con LLM](analisis-manual-llm.md): propuesta descriptiva complementaria; no forma parte de las llamadas de la CLI local.

Para modificar señales, pesos, umbrales o preprocesado se necesita identificar una nueva versión de señal y definir datos de confirmación independientes antes de evaluar la mejora. Reproducir un benchmark consumido no lo convierte en un conjunto nuevo.
