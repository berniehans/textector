# Auditoría de zippy 0.1.3 (Thinkst) — fórmula para el port a textector

**Fecha**: 2026-10-24 · fact-check de diseño, sin copiar código.
**Fuente leída aquí**: `.../hermes/cache/scratch/uv-venv/Lib/site-packages/zippy/zippy.py`
(+ su data `ai-generated.txt` como semilla EN del propio paquete).

## 1. Fórmula exacta observada en el código

Notación: `c(x)` = bytes comprimidos; `len(x)` = bytes UTF-8 de x.

Definición base (todas las engines):
- `ratio(x) = c(x) / len(x.encode('utf-8'))` — ratio de compresión.

**LZMA** (`LzmaLlmDetector`, default en `Zippy`, `preset=4`):
- `ratio(x)` con `lzma.LZMACompressor(preset=4)` + `flush()`.
- Base (sin normalizar): `delta = ratio(prelude) − (c(prelude+sample)/len(prelude+sample)) `...
  según `score_text`: `delta = prelude_ratio − prelude_ratio` NO; la línea real es
  `delta = self.prelude_ratio - (c(prelude+sample)/len(prelude+sample))` cuando
  `normalize=False` — el término de corrección `(self.nf * ...)` es 0.0 sin `-n`.
- Con `normalize=True` (`flag -n`): `nf = prelude_ratio / len(prelude_str)` y
  `delta = prelude_ratio − (c(prelude+sample)/len(prelude+sample) − nf*len(sample)*len(sample)/len(prelude_str))`.
  OJO: hay un bug conocido y RESUELTO aquí (definido así en el archivo): el
  término de corrección se aplica dentro del paréntesis (resta al ratio de
  muestra, sube el delta); es el gesto de "normalizar la contribución del sample".
- Veredicto: `delta < 0 → Human`, sino `AI`; "confianza" emitida = `abs(delta*100)`.

**Brotli** (`BrotliLlmDetector`, `preset=8`, `lgwin=24`, `MODE_TEXT`):
- mismo diseño, sin corrección de longitud (no soporta `normalize`).

**Zlib** (`ZlibLlmDetector`, `preset=9`, raw deflate `wbits=-15`, `memLevel=9`):
- prelude splits en chunks con `numpy.array_split(lines, ceil(len(prelude)/2**15))`
  y `prelude_ratio = mean(ratio(chunk_j))`; sample se evalúa anexado a cada chunk.

**Chunking general** (`Zippy.run_on_text_chunked`, default `chunk_size=1500`):
- cortes por el último espacio (`rfind(' ', start, start+chunk_size+1)`);
- score por chunk; agregación: `sum(s[1] * len(chunk_i)/len(total))` con signo
  por veredicto (`AI` resta, `Human` suma); signo final decide el veredicto.

**Semilla**: `PRELUDE_FILE = 'ai-generated.txt'`, texto EN generado por IA
incluido en el paquete (<100 KiB según el post de Thinkst de 2023-06-09;
tamaño EXACTO no verificado aquí).

**Limpieza** (`clean_text`): `' +'→' '`, sin `\t`, `'\n+'→'\n'`, sin espacios
junto a `\n`, y elimina TODA carácter fuera de `[0-9A-Za-z,.() \n]` (nota:
eso elimina acentos y ñ; ver §3).

## 2. Discussion #5 del repo

`[unverified]` — no accesible en esta sesión (proveedor de extracción web no
disponible; la URL `github.com/thinkst/zippy/discussions/5` se identificó via
búsqueda pero no se pudo abrir sin navegador). La fórmula y la normalización
documentadas aquí salen DIRECTAMENTE del código `zippy.py` leído, cumpliendo la
vía alternativa que exige el brief. Si en F2/F3 se confirma la discussion,
revisar si añade contexto de umbrales/limpieza que corriga lo antedicho.

## 3. Qué porta textector y qué no

**Porta (concepto, no código)**:
- Idea central: mediar "novedad/perplexidad" por ratio de compresión contra
  semilla de texto AI, con delta con signo y reflejo de veredicto.
- La fórmula base SIN corrección de normalización (`normalize=False`) como
  primera implementación stdlib (`lzma`, `preset=4`), y la ruta de chunking
  con corte por espacio y agregación ponderada por longitud de chunk.
- Los límites de sanidad del chunking (`chunk_size ~1500`) y el aviso de
  zippy: sin chunking, un sample grande "traga" al prelude y aplana el ratio.

**No porta**:
- Brotli (dependencia externa; textector es stdlib-only).
- numpy (`array_split`); el chunking ES de textector será stdlib puro
  (slices/python puro).
- La semilla `ai-generated.txt` EN tal cual: para ES es insuficiente y además
  no es redistribuible sin verificar licencia. La semilla ES (si aplica)
  se decide en F3 con corpus propio; sin semilla ES, el check de compresión
  NO corre para español (fail-closed, `insufficient=True`).
- El "confidence" `abs(delta*100)` como número publicable: en textector solo
  será una señal acotada [0,1] dentro de `CheckResult`, nunca probabilidad
  ni prueba de autoría (límite fundamental del proyecto).

**Adaptación ES**: `clean_text` del referencial destruye tildes y ñ
(`re.sub(r'[^0-9A-Za-z,...]')`). El preprocesado ES de textector debe
conservar `a-z` con diacríticos (`á é í ó ú ü ñ`) y las rayas de diálogo en
la limpieza, o la señal ES será ruidosa.

## 4. Estado del port en F1

F1 no implementa nada de compresión (sin I/O, sin semilla); este documento
fija la ESPECIFICACIÓN que F2 convertirá en check con `CheckResult`.
Umbrales no definidos en F1: backlog de calibración F3.
