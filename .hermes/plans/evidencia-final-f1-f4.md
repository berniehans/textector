# EVIDENCIA FINAL — textector F1…F4 (24-oct-2026)

- **F1** GREEN: 30 tests OK (8 skips activables). Segmentador ES verificado manual.
- **F2** GREEN: 76/76 tras fix de fronteras (uniformity ventana [0.15,0.40]; invarianza de compresión DIRECCIONAL).
- **F3** hecho con veredicto honesto: corpus 10+10 (10 Gutenberg-PD ES + 10 producidos por Hermes glm-5.3-flash/aattr), manifest.csv con procedencia (SHA256 parcial: quedó hash para completar en 2 filas según notó el coder), semillas construidas SOLO de train-IA; holdout {h03,h04,h08,a05,a09} evaluado UNA vez: matriz TP=2(IA), FN=0, FP=3 (prosa clásica ES→"ia"), TN=0, abstención=1 → **tasa FP alta → el índice queda como PRE-FILTRO con abstención, nunca detector confiable** (etiqueta experimental).
- **F4** GREEN: 84/84 (incluye los 5 del CLI). Fix del test harness: orden de `--config` en `_run()` (el hardcoded pisaba el del caso). Parser YAML-min fail-closed endurecido (claves raíz limitadas a version/phrases/cliches; validación post-valores para preservar mensajes tag/alias).
- **uv.lock REAL** generado con `uv lock` + `uv sync` (130 B; proyecto sin dependencias runtime).
- **SMOKE final CLI** (texto externo composer-pastes, sin etiqueta, sin conclusión de origen, exit 0):
```json
{"contribuciones": {"burstiness": 1.24, "cliches_es": 24.06, "compression": 11.99, "mattr": 0.0, "uniformity": 0.0}, "indice_llm": 37, "insufficient_text": false, "n_disponibles": 5}
```

## Pendientes de orden humana

1. **Commit del parche core Hermes** (hermes-agent: `agent/session_client_env.py` + `profiles/coder/plugins/coder-auto-route` 1.0.1) — repo dirty; requiere orden de commit y, si procede, reporte upstream del bug (caché del gateway + sanitizer HERMES_*).
2. **git init/commit del propio textector** (sin push salvo orden).
3. Mejora de señal (opcional): más corpus (20–30 piezas) o aceptar el rol de pre-filtro.
