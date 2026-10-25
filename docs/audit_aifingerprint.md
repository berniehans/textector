# Auditoría de aifingerprint 1.6.0 — port a textector (F1)

**Fecha**: 2026-10-24 · **Tipo**: fact-check de diseño, sin copiar código.
**Fuente leída (vía read_file, aquí mismo)**:
`.../hermes/cache/scratch/uv-venv/Lib/site-packages/aifingerprint/`

## 1. Arquitectura observada

| Archivo | Contenido |
|---|---|
| `analyzer.py` | `analyze(text) -> (score, results)`: normaliza, ejecuta todos los checks, suma `raw_score * CATEGORY_WEIGHTS[name]`, acota `max(0, min(100, int(round(*100))))` y etiqueta CLEAN/MILD/NOTICEABLE/OBVIOUS/BLATANT (`score_label`). |
| `checks/__init__.py` | `CheckResult = tuple[list[str], float]` (`hits`, `raw_score`) y dict `CHECKS` con 10 checks. |
| `checks/*.py` | 10 checks: vocabulary, phrases, structure, formatting, tone, sentence_rhythm, punctuation, connectives, burstiness, compression. Cada uno firma `check(text, lines) -> (hits, raw)` — funciones puras, deterministas. |
| `patterns.py` | Base de datos: `BANNED_WORDS` (por categoría gramatical), `BANNED_PHRASES` (opener/hedging/transition/closing/hype/faux_conversational/pleasantries/weasel), `BANNED_SENTENCE_STARTERS`, `SENTENCE_PATTERNS` (tricolon, positive paralelismo, etc.), `ENTHUSIASM_WORDS`, `HEDGE_WORDS`, `DISCOURSE_CONNECTIVES`, `FORMAT_PATTERNS` y `CATEGORY_WEIGHTS` (compression 0.20, sentence_rhythm 0.15, tone 0.15, punctuation 0.12, connectives 0.10, burstiness 0.08, vocabulary 0.08, structure 0.07, phrases 0.05, formatting 0.00). |
| `text.py` | `normalize_text` (NFKC + invisibles + homoglyfos + NFD-suelta-acentos), `split_sentences` (con abreviaturas EN y placeholders), `split_paragraphs`, `word_overlap`, `find_line`. |
| `checks/compression.py` | Seed corpus propietario `data/ai_seed_corpus.txt`; similitud `1 - overhead/text_alone` con LZMA; umbrales `SIMILARITY_HIGH=0.45`, `MODERATE=0.38`, mapping lineal `[0.30, 0.50] -> [0,1]`; guías de límite `MIN_TEXT_BYTES=100`, `MAX_TEXT_BYTES=1MB`. |

## 2. Qué se porta a F2 (y por qué)

1. **El contrato de checks**: firma única `(hits, raw)` puro y determinista con
   score normalizado en [0,1] agregado por pesos y acotado a [0,100].
   Razón: hace el índice explicable (cada check contribuye y se puede citar)
   y permite calibrar solo pesos, sin tocar checks. Ya formalizado en
   `tools/checks/` como `CheckResult` (dataclass adicionando
   `peso/contribucion/coverage/insufficient`) y familia `Check`.
2. **Check de punctuation (entropía de Shannon normalizada)** en
   `checks/punctuation.py`: entropía sobre distribución de signos, normalizada
   contra `log2(6)` fijo (decisión acertada: baseline fijo evita covariación con
   el input), y mapping lineal `[0.20, 0.60] -> [1,0]`. Es portable a ES tal
   cual, añadiendo los signos APERTURA `¿ ¡` y comillas latinas `«»` a la
   clase de puntuación — suma señal positiva para español.
3. **Check de sentence_rhythm (CV de longitud de oraciones)** en
   `checks/rhythm.py`: coeficiente de variación con std muestral (N-1),
   mínimo 10 oraciones para fiabilidad, mapping `[CV 0.30..0.70] -> [1,0]`.
   Razonable para ES; los umbrales se recalibran en F3 con corpus ES.
4. **Check de burstiness/vocabulario por densidad** (estructura "proporción
   por 1000 tokens" en los checks): el mecanismo densidad-trié por ventana
   es port directo; las LISTAS de palabras NO se portan (ver §3/§4).
5. **El listado de checks+pesos** (`analyzer.py` + `patterns.py::
   CATEGORY_WEIGHTS`) como PUNTO DE PARTIDA documental de pesos en F3: los
   pesos del referencial vinieron de pruebas con corpus (comentarios en
   código: "AI leave-one-out mean ~0.47, human mean ~0.36" para compresión;
   "AI mean CV ~0.45, human ~0.72" para ritmo); textector recalibra con
   corpus ES propio (F3) y no heredará esos números sin verificación.

## 3. Qué se adapta a ES (y cómo)

- **normalize_text**: el referencial pierde tildes (NFD + drop diacríticos) y
  fuerza ASCII. En español eso colapsa palabras distintas ("canción" vs
  "cancion" están bien para matching, pero "ño" / "no" NO son la misma
  palabra). textector: NFC + casefold, SIN drop de diacríticos
  (`tools/textector_core.py::normalize_text`).
- **split_sentences**: lista de abreviaturas EN (Mr/Mrs/vs/e.g…) se sustituye
  por la ES (Sr/Sra/p. ej./etc.; compuestos con punto interno "p. ej.") y se
  añaden reglas conservadoras que el referencial no tiene: elipsis nunca
  separa, punto decimal no separa, `¿ ¡` como aperturas condicionales, y la
  raya de diálogo «—» no es terminal (`—La conoces —me dijo.` una oración).
  También se exige spans (start, end) sobre el texto original: el referencial
  devuelve frases sin posición, útil para hablar, insuficiente para evidencia.
- **SENTENCE_PATTERNS/ BANNED_PHRASES EN**: se documentan como semántica de
  referencia; las listas EN NO se traducen literal — el léxico ES se arma
  desde el corpus de clichés (`textector-insumos/ai-cliches-corpus.json`,
  758 entradas EN como semilla temática) y revisión manual ES en F2.
- **participial_ending / copulative_avoidance**: en ES el equivalente es el
  gerundio final ", haciendo X." y las cópulas "sirve como/en/a": se
  planean para F2 como patterns ES distinto al EN original.

## 4. Qué se descarta (con motivo)

- **Homoglyph fold y NFKC-agresivo de `text.py`**: cámara anti-evasión EN
  (cyryllic lookalikes, fullwidth); en español real es ruido y destruye
  diacríticos. Se reemplaza por una lista mínima de invisibles.
- **el check "compression"** (`checks/compression.py`): es la misma familia
  que zippy (LZMA con seed). DECISIÓN DE F1: en textector, la señal de
  compresión se implementa con el port de zippy (auditoría dedicada,
  `docs/audit_zippy.md`), con semilla SEPARADA y normalización documentada;
  NO se usa `ai_seed_corpus.txt` del paquete (licencia/peso no verificados
  para redistribuir). Si zippy se portara con la semilla EN, en ES haría
  falta semilla ES (F3).
- **etiquetas categóricas de salida** (`score_label` CLEAN/BLATANT): pediría
  interpretar el índice como diagnóstico; el deliverable de textector es el
  índice + evaluación con contribuciones y limits (ver README).
- **formatting check con peso 0.00**: ni señal ni costo → en textector solo
  se agarra cuando un consume peso > 0; en F2 se revisa si un check de
  formato ES merece peso o se descarta igual.

## 5. Riesgos del port (F2/F3)

1. `BANNED_WORDS` sesga textos de marketing/EN; en ES hay falsos positivos
   ("gancho", "revolución") si se traduce directo — requiere corpus ES real.
2. Los umbrales del referencial se midieron contra sus corpus, no contra ES:
   son hipótesis, no constantes — F3 recalibra todo.
3. La lista de clichés más larga CREA señal plateada fácil de evadir: los
   checks deben priorizar métricas densidad (CV, entropía, conectores por
   1000 palabras) sobre matching literal.
