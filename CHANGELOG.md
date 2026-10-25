# Cambios

## 0.3.0 — 2026-10-25

- Añade el perfil optativo `f5-portable-v1` (`--metodo f5`) con pesos fijos,
  abstención explícita y señales de ritmo/párrafo fuera del índice. F4 sigue
  siendo el perfil predeterminado.
- Añade calibración reproducible sobre datos de desarrollo y comparación
  congelada con F4 en un conjunto reservado de 536 textos. F5 pasa las cuatro
  cotas declaradas antes de puntuar, pero sigue siendo experimental: la detección
  de IberAuTexTification es baja y los resultados no demuestran generalización
  a autores ni proveedores nuevos.
- Añade restauración y verificación SHA-256 de los corpora; no distribuye los
  textos fuente con restricciones de licencia.
- Repara integridad de recursos, preprocesado Unicode, cobertura, diagnósticos,
  calibración por grupos y empaquetado del wheel.
- Verificación local: 159 pruebas unitarias y smoke test del wheel instalado
  fuera del checkout, con F4 y F5.

El índice es una señal de estilo, no probabilidad ni prueba de autoría. Consulte
`docs/validacion-f5-portable.md` y `docs/validacion-externa-v1.md` para los
resultados y límites de los corpora.
