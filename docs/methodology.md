# Methodology — textector F2 (índice heurístico explicable, español)

**Estado: experimental. Congelado en F2; F3 recalibra umbrales con corpus ES
real (los pesos NO se optimizan en F3 — quedan fijados aquí).**

> Límite fundamental: `indice_llm` es un **índice heurístico**: indicio,
> NO probabilidad de generación y NO prueba de autoría. Nunca usarlo para
> acusar a una persona. Ningún número de este documento fue validado contra
> corpus ES real; provienen de hipótesis de diseño tomadas de los
> referenciales MIT (ver NOTICE) y se etiquetan PROVISIONAL.

## 1. Índice

    contribucion_i = 100 · w_i · q_i / Σ(w de checks disponibles)
    indice_llm     = int(round(Σ contribuciones))   ∈ [0, 100]

- Solo checks disponibles (`insufficient=False`) participan en numerador y
  denominador (renormalización por cobertura).
- `suma_contribuciones` es el valor exacto; el índice publicado es la suma
  redondeada a entero (único redondeo declarado del pipeline).
- Los checks insuficientes NO puntúan su contribución (q=0 sin peso
  fantasma) y reportan `insufficient=True` en su CheckResult.
- Si NINGÚN check corre: `insufficient_text=True`, `indice_llm=None`
  (abstención; el CLI F4 saldrá con exit ≠ 0).
- JSON del reporte: claves ordenadas (`json.dumps(..., sort_keys=True)`),
  valores determinista-crudos. Sin azar, sin red, sin I/O de red, sin
  relojes: reproducible bit a bit para el mismo input.

## 2. Pesos congelados (Fuente única: `tools/scoring.py`)

| check        | peso w | correlación con |
|--------------|-------:|-----------------|
| burstiness   | 0.18   | mattr (ritmo/variedad) |
| mattr        | 0.17   | burstiness |
| uniformity   | 0.18   | cliches_es |
| cliches_es   | 0.24   | uniformity |
| compression  | 0.23   | (independiente) |

Suma base = 1.00. Tope de peso CONJUNTO para grupos potencialmente
correlacionados (corrige doble conteo de una misma fuente de señal):

- (mattr, burstiness)  ≤ 0.32
- (cliches_es, uniformity) ≤ 0.40

Si el grupo excede el tope, ambos pesos del grupo se reescalan por el mismo
factor (tope/suma). El denominador de contribuciones usa los pesos
post-tope (Σ = 0.95 con los 5 checks disponibles → contribuciones suman el
índice exacto por construcción).

Clasificación de checks (la dirección es una hipótesis de diseño F2, no una
regla universal; F3 la contrasta contra corpus):

| check        | "LLM" es...                       | PROVISIONAL |
|--------------|-----------------------------------|-------------|
| burstiness   | oraciones de largo similar         | sí |
| mattr        | vocabulario local pobre            | sí |
| uniformity   | párrafos parecidos, aperturas repetidas | sí |
| cliches_es   | clichés narrativos del corpus      | sí |
| compression  | estilo más predecible para semilla IA | sí |

## 3. Transformaciones congeladas por check

Valores crudos → q en [0, 1]; luego el scoring los pondera.

### burstiness (`tools/checks/burstiness.py`)
- Entrada: longitudes en tokens de cada oración (`split_sentences` ES),
  excluye oraciones sin tokens.
- cv_robusto = MAD(longitudes) / mediana(longitudes) — mediana y MAD, NO
  media/std: los extremos (elipsis, réplica) no mandan. Nota: el
  referencial usaba CV clásico; el rango difiere (un cv_robusto suele
  ser ~0.5× el CV std).
- q = clamp(1 − (cv_robusto − 0.20) / 0.40).
  cv ≤ 0.20 → 1.0 (uniformidad máxima); cv ≥ 0.60 → 0.
- `insufficient` si oraciones con tokens < 10. `n_dialogo` reportado
  (las réplicas con raya cuentan como oración normal: el MAD las absorbe,
  documentado en §5 limitaciones).
- Invarianza a duplicar: EXACTA (mediana/MAD no cambian con masa duplicada).

### mattr (`tools/checks/mattr.py`)
- MATTR con ventana fija = **50 tokens** (deslizamiento 1; promedio simple
  de TTR por ventana). Texto < 50 tokens → `insufficient` (nunca se
  sustituye TTR global en silencio; eso cambiaría la semántica del número).
- q = clamp(1 − (mattr − 0.55) / 0.30). mattr ≤ 0.55 → 1.0
  (vocabulario pobre); ≥ 0.85 → 0 (rico).
- Invarianza a duplicar: APROXIMADA (las ventanas que cruzan la unión
  difieren; tolerancia observada ≈0.02 en mattr).

### uniformity (`tools/checks/uniformity.py`)
Dos indicadores SEPARADOS (reportados crudos en `valor_bruto`):
- q_dispersion = clamp(1 − (cv_parrafo − 0.15) / 0.25), donde
  cv_parrafo = MAD/mediana de longitudes de párrafo en tokens
  (párrafos separados por línea en blanco). Frontera AJUSTADA en el gate
  F2 del desarrollador (HIGH 0.60 → 0.40): con la curva (0.15, 0.60) un
  ensayo ES claramente variado —p. ej. párrafos de 8, 26, 10, 34, 14 y 30
  tokens, cv_parrafo ≈ 0.35 y aperturas todas distintas— daba
  q ≈ 0.28 (≥ 0.2), es decir, señal de variedad falsa; con la
  ventana [0.15, 0.40] da q_disp ≈ 0.22 y q ≈ 0.11 < 0.2 (correctamente
  bajo el corte), y un cv_parrafo ≥ 0.40 —máxima variedad de prosa ES—
  no aporta señal de dispersión. F3 puede recalibrar el corte, no el peso.
  La dirección "párrafo uniforme = señal" es la hipótesis del port.
- q_repeticion = clamp((share_apertura_max − 0.22) / 0.33), donde
  share_apertura_max = máxima fracción de párrafos de prosa que comparten
  los mismos 2 primeros tokens. Los párrafos de réplica (empiezan con
  «—»/«–») se cuentan aparte (`n_dialogo`); si no hay prosa, se reporta
  `sin_prosa=True` y q_repeticion=0 (no señal artificial).
- q = (q_dispersion + q_repeticion) / 2.
- `insufficient` si párrafos < 3.
- Invarianza a duplicar: EXACTA en q_dispersion; EXACTA en q_repeticion
  (la share no cambia al duplicar los párrafos).

### compression (`tools/checks/compression.py`) — método zippy redefinido
- Deflate RAW stdlib: zlib.compressobj(level=6, wbits=-15) — c(x)=len(bytes).
- Limpieza ES conservadora: tokens casefold unidos por espacio (conserva
  tildes/ñ: DIFERENCIA deliberada frente a clean_text de zippy, quien
  las borra; la puntuación y el ruido se desvanecen con la tokenización).
- Marginal normalizado por bytes del texto:
    m_seed = (c(seed_clean + " " + sample_clean) − c(seed_clean))
             / bytes(sample_clean)
  m bajo = la semilla predice bien la muestra (proxy de perplejidad; mimetiza la
  perplejidad sin modelo).
- delta = m_ia − m_h; q = clamp(0.5 − delta / 0.40).
  Sample en estilo de la semilla IA → m_ia bajito → delta<0 → q>0.5.
- MIN_BYTES_MUESTRA = 150 bytes de muestra limpia, sino insufficient.
  MAX_TOKENS = 30000 (por encima, se trunca y se etiqueta
  `muestra-truncada`; sin chunking en F2 — el límite zippy de "una muestra
  grande traga al prelude" no aplica al diseño marginal, documentado).
- Semillas: SINTÉTICAS deterministas embebidas (fixture de MECÁNICA; no
  miden desempeño real). Las ES reales (solo del subconjunto IA del
  train de F3) reemplazan `semilla_ia()`; la humana se mantiene sintética
  complementaria o se sustituye con el train humano de F3.
- Invarianza a duplicar: DIRECCIONAL (invariante CORRECTO, decidido en el
  gate F2): al duplicar la muestra el VALOR de delta/q NO es invariante —
  deflate re-consume redundancia y el delta baja (~0.16 en q al x2) —
  pero la DIRECCIÓN sí se conserva: la muestra queda en el mismo lado del
  umbral 0.5 (corte IA/H). El valor exacto de ese umbral (y de la escala
  delta) se fijan por train en F3; en F2 solo se garantiza el lado
  (q>0.5 en fixtures IA, q≤0.5 en humanas).

### cliches_es (`tools/checks/cliches_es.py`)
- Léxico en `config/cliches_es.yaml` (YAML-min fail-closed; clave raíz
  `cliches`, entradas `"frase|peso|fuente"`; `phrases` legacy queda `[]`
  por el contrato del esqueleto F1). Mínimo embebido determinista si no
  se pasa lexicon.
- Matching de SECUENCIA CONTIGUA de tokens exactos con comodín `__`
  (exactamente un token), greedy izquierda→derecha no-ambiguo, casefold.
- Densidad ponderada = Σ((peso/10)·n_hits) · 1000 / n_tokens
  (peso yaml = 0..100 estilo corpus; unidades 0..10).
- q = clamp(densidad / 2.5).
- `insufficient` si tokens < 50.
- Salida ANONIMIZADA: hits = {id, pos, fin} por índice de token + conteos
  por entrada; el texto crudo del hallazgo NUNCA aparece en el reporte
  (privacidad: no se regurgita prosa del analysed).
- Invarianza a duplicar: EXACTA (conteos y denominador escalan por 2).
- Falso positivo conocido y DOCUMENTADO (§5): frases de alta frecuencia en
  español normal ("en el fondo", "de quien", "el peso de la") pesan poco
  (12-26) y F3 mide su FP rate en corpus humano; si suben, se descartan.

## 4. Umbrales provisionales (tabla única)

| parámetro                          | valor | fuente |
|-----------------------------------|-------|--------|
| burstiness cv_robusto [LOW, HIGH] | 0.20, 0.60 | hipótesis F2 (referencia: CV std AI~0.45/humano~0.72) |
| mattr ventana                     | 50    | diseño F2 |
| mattr [min, max] señal            | 0.55, 0.85 | hipótesis F2 |
| uniformity cv_parrafo [LOW, HIGH] | 0.15, 0.40 | hipótesis F2; HIGH ajustada en el gate F2 (ver §3) |
| uniformity share apertura [min,max]| 0.22, 0.55 | hipótesis F2 |
| compression escala delta          | 0.40  | hipótesis F2 |
| compression min bytes muestra     | 150   | diseño F2 |
| compression max tokens            | 30000 | diseño F2 |
| cliches min tokens                | 50    | diseño F2 |
| cliches densidad saturación       | 2.5 / 1000 tokens | hipótesis F2 |
| pesos (5 checks) y topes de grupo | ver §2 | CONGELADOS F2 |

"Congelado" se usa en el significado exacto de F2: NO se optimizó, no se
calibró contra corpus ES; solo se SELLÓ para que F3 evalúe (y de ser
necesario recalibre los UMBRALES, no los pesos).

## 5. Limitaciones (explícitas, no negociables)

1. **No probatorio**: el índice es sospecha suave. Un índice 0 no prueba
   autoría humana; un índice 100 no prueba uso de IA.
2. **Umbrales no calibrados**: F3 corre CV por grupos en corpus 20; hasta
   entonces el índice solo sirve para triaje comparativo, no para decisión.
3. **Anáfora literaria y estilo formal**: la repetición de aperturas
   (uniformity) y la uniformidad rítmica (burstiness) detectan también
   estilos humanos deliberadamente repetitivos (anáfora, prosa legal,
   narración infantil). Limites documentados, no corregidos — abstención
   per-check cubre textos cortos pero no este sesgo de estilo.
4. **Diálogo**: las réplicas con raya cuentan como oración en
   burstiness y como párrafo no-prosa en uniformity; el efecto neto de un
   texto mayormente diálogo es hipótesis sin medir.
5. **Clichés FP**: ver §3 — frases comunes pesan poco; el matching es de
   superficie (no semántica); evadir es trivial (parafrasear), y eso
   reduce la utilidad para evasores pero también la señal general.
6. **Compression con semilla sintética en F2**: los números q de este
   check NO son los que darán la semilla ES real de F3; el check valido
   mecánica y determinismo, nada más.
7. **composer-pastes**: fuera del alcance de la herramienta (no puntuar
   pastes del composer; la CLI F4 es la frontera).
8. **Idioma**: diseñado SOLO para español; en otros idiomas los
   indicadores son ruido con pretensiones de señal (no se dare uso).
9. **Compression: valor no invariante a longitud**: al duplicar una
   muestra delta/q baja (~0.15 en q) porque deflate re-consume
   redundancia; lo invariante es la DIRECCIÓN respecto del umbral 0.5.
   F3 fija ese umbral (y la escala delta) con train; el q de F2 no se
   compara como magnitud entre textos de distinta longitud.

## 6. Qué valida la suite F2 (y qué no)

- Sí: contratos, transformaciones, pesos/topes, abstención,
  invarianzas, determinismo, registro (5 checks), anidación del
  scoring sobre CheckResult real.
- No: efectividad detectiva en ES real (F3), ni comparación con
  referenciales externos (piloto, máquina del maestro).
