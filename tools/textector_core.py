"""Núcleo de texto de textector: funciones puras, sin I/O ni red.

Puerto adaptado (desde especificación, no por copia) de utilidades de
segmentación de texto de proyectos referenciables con licencia MIT
(aifingerprint 1.6.0, ver docs/audit_aifingerprint.md).

Diferencias deliberadas frente al referencial:
- normalize_text NO elimina diacríticos: en español la raya "ñ" y las tildes
  son distintivas del idioma; solo se normaliza Unicode (NFC) + casefold.
- split_sentences devuelve *spans* (start, end) sobre el texto ORIGINAL,
  requerido por los checks explicables para citar evidencia sin re-slicing.
- Conservador: ante ambigüedad (elipsis, abreviatura dudosa) NO separa
  oraciones; prefieren menos cortes a cortes falsos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = ["Span", "normalize_text", "tokenize", "split_sentences"]

# Elementos invisibles que pueden fingir límites de palabra o evadir matching.
# Se eliminan porque no aportan contenido en español (denominador de evasión).
_INVISIBLE_RE = re.compile(
    "[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\u00ad\ufeff\u180e"
    "\U0001f100-\U0001f1ff]"
)


@dataclass(frozen=True)
class Span:
    """Fragmento del texto original, con posición para evidencia explicable."""

    text: str
    start: int
    end: int


def normalize_text(text: str) -> str:
    """Normaliza Unicode a NFC, casefold, y elimina caracteres invisibles.

    - NFC (no NFD): conserva las letras base con tilde una sola vez ("á"),
      algo esencial para el español.
    - casefold: comparación insensible a mayúsculas.
    - Elimina solo invisibles (zero-width, soft hyphen, BOM); NO elimina
      diacríticos ni homoglifos Cyrillic/Greek: el corpus objetivo es
      español real, y cambiarlos sería alterar el texto a evaluar.

    El texto devuelto NO conserva offsets: los checks citan evidencia con
    spans (split_sentences) sobre el texto original o sobre subventanas.
    """
    if not isinstance(text, str):
        raise TypeError("normalize_text espera str")
    text = unicodedata.normalize("NFC", text)
    text = _INVISIBLE_RE.sub("", text)
    return text.casefold()


# Token = secuencia de letras/dígitos Unicode (incluye ñ, tildes, acentos).
# Aplica sobre el texto casefold para que "Casanova" == "casanova".
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokeniza en palabras Unicode (sin modelos más allá del propio regex stdlib).

    Se usan categorías Unicode (\\w) por lo que ñ, tildes, árabes, griegos, etc.
    se tokenizan de forma estándar; la puntuación y los espacios separan tokens.
    Números y tokens alfanuméricos se devuelven tal cual (casefold).
    """
    return [m.group(0) for m in _TOKEN_RE.finditer(normalize_text(text))]


# ---------------------------------------------------------------------------
# Segmentación de oraciones (español, conservador, con spans)
# ---------------------------------------------------------------------------

# Abreviaturas cuyo punto final NO debe cortar oración. Se comparan sobre el
# texto casefold y solo se admite la forma sin punto interno hasta el operador.
# Los compuestos con punto interno ("p. ej.", "s. f.") se listan aparte.
_ABBREV_TOKENS = frozenset(
    {
        # Títulos y personas
        "sr", "sra", "srta", "dr", "dra", "lic", "prof", "profa", "ing",
        "mtro", "mtra", "psic", "ab", "ram", "cpa", "gen", "col", "cap",
        # Lugar / tiempo
        # F5.4: fuera " rej" (entrada muerta: el token previo sale de \w+,
        # nunca con espacio) y "no" (palabra común, no abreviatura).
        "av", "avda", "sta", "sto", "ste", "ctra", "nro",
        # Técnicos / escritura académica
        "etc", "cf", "véase", "vs", "aprox", "fig", "lám", "pág", "pp",
        "vol", "núm", "ed", "op", "cap",
        # F5.4: fuera "pt", "a", "h", "ib", "s", "ss", "g", "m", "l" —
        # redundantes: el centinela _SINGLE_LETTER_DOT_RE ya cubre tokens
        # de 1-2 letras (misma conducta, sin cambiarla).
        "iva", "igv", "km", "cm", "mm", "kg",
    }
)

# F5.4: palabras comunes cuyo punto SÍ corta oración (no son abreviaturas
# ni iniciales): p. ej. «Dijo que no. Luego se fue.». Excepción deliberada
# al centinela de 1-2 letras, que si no las tragaría como dudosas.
_PALABRAS_CORTE = frozenset({"no"})

_ABBREV_RANGE = (
    # compuestos con punto interno en minúscula: "p. ej.", "s. f.", "n. del a."
    ("p", "ej"),
    ("s", "f"),
    ("n", "del", "a"),
    ("m", "e", "c"),
)
# Sentinel: token genérico (una o dos letras más punto) es abreviatura dudosa;
# en proveedor conservador vale: NO cortar.
_SINGLE_LETTER_DOT_RE = re.compile(r"\b[a-záéíóúñü]{1,2}\.\Z")


def _is_abbrev_breakage(text: str, end: int) -> bool:
    """True si el '.' en ``text[end-1]`` NO debe inducir corte de oración.

    Inspecciona el token previo en el texto original; se acepta un margen
    blanco hacia atrás solo cuando es multi-punto ("p. ej.").
    """
    # "p. ej." / "s. f." / "n. a." — compuestos: mirar dos tokens atrás.
    m = re.search(r"\b(\w+(?:\.\w+)+)\.\Z", text[:end], re.UNICODE)
    if m:
        parts = m.group(1).split(".")
        for frag in _ABBREV_RANGE:
            if [p.casefold() for p in parts] == [p.casefold() for p in frag]:
                return True
    prev = re.search(r"\b(\w+)\.\Z", text[:end], re.UNICODE)
    if prev:
        tok = prev.group(1).casefold()
        if tok in _ABBREV_TOKENS:
            return True
        if tok in _PALABRAS_CORTE:
            return False
        # dudoso: "Sr.", "vs." vienen arriba; "X. N." iniciales → no cortar
        if _SINGLE_LETTER_DOT_RE.match(tok + "."):
            return True
    return False


_TERMINAL_RE = re.compile(r"([.!?…])([\u00bb\u201d\"')\]]*)")
_OPENERS = "\u00ab\u201c\"([('¿¡"

# Línea de encabezado tipo «S01 — Escena inicial»: no es prosa.
_HEADER_RE = re.compile(r"^#{0,3}[ \t]*[Ss]\d+(?:[ \t]*[—–:-][ \t]*[^\n]+)?[ \t]*$")


def _next_nonspace(text: str, start: int) -> tuple[str, bool]:
    """Par (primer carácter no blanco desde ``start``, ¿hubo '\\n' antes?).

    Devuelve ('', False) si no queda nada tras los blancos. El flag de
    nueva línea se usa para la regla de la raya: solo delimita en
    inicio de línea.
    """
    m = re.match(r"(\s*)(.)", text[start:], re.DOTALL)
    if not m:
        return "", False
    return m.group(2), "\n" in m.group(1)


def split_sentences(text: str) -> list[Span]:
    """Segmenta en oraciones en español de forma conservadora.

    Reglas:
    - Terminales [.!?] pueden separar oración; «…»/«...» no (elipsis conservadora).
    - El punto de una abreviatura (Sr., p. ej., etc., talla corta) no separa.
    - El punto decimal (1.50 / 1,50) no separa.
    - Raya de diálogo de réplica («—La conoces —me dijo.») no fuerza corte:
      «—» nunca es terminal; el punto final cierra la oración completa.
    - Una oración nueva exige, tras el terminal blanco(s), mayúscula o apertura
      (¿ ¡ « "( ) — raya de diálogo a comienzo de réplica).
    - Encabezados de tipo «S01 — …» (con guion largo tras etiqueta) NO cuentan
      como prosa y se filtran del resultado.

    Devuelve ``Span`` con ``start``/``end`` sobre el texto original (inclusivo-
    exclusivo), sin I/O ni red. Texto vacío/solo blancos → [].
    """
    if not isinstance(text, str):
        raise TypeError("split_sentences espera str")
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _TERMINAL_RE.finditer(text):
        end_idx = m.end()
        ch = m.group(1)
        if ch == "…":
            continue  # elipsis: nunca corta (conservador)
        if ch == ".":
            if (m.start() > 0 and text[m.start() - 1] == ".") or (
                m.start() + 1 < len(text) and text[m.start() + 1] == "."
            ):
                continue  # elipsis ASCII: ninguno de sus puntos corta
            # decimal: dígito '.' dígito inmediato en el texto original
            if m.start() > 0 and text[m.start() - 1].isdigit():
                window = text[m.start() - 1 : m.end()]
                if re.match(r"\d\.\d", window):
                    continue
            if _is_abbrev_breakage(text, m.end()):
                continue
        nxt, newline_before = _next_nonspace(text, end_idx)
        if not nxt:
            continue
        is_upper = nxt.isalpha() and nxt == nxt.upper() and nxt != nxt.lower()
        # La raya solo delimita en inicio de línea (réplica nueva); dentro
        # de la misma línea («—La conoces —me dijo.») nunca es terminal.
        is_opener = nxt in _OPENERS or (nxt == "\u2014" and newline_before)
        if not (is_upper or is_opener):
            continue
        spans.append((start, end_idx))
        start = end_idx
    if start < len(text):
        spans.append((start, len(text)))

    out: list[Span] = []
    for a, b in spans:
        frag = text[a:b]
        if not frag.strip():
            continue
        # Encabezados tipo «S01 — ...»: se filtran por LÍNEA (no por
        # fragmento completo, que puede incluir prosa tras el encabezado).
        # Las líneas de prosa conservadas se agrupan en corridas contiguas:
        # una corrida = un Span con offsets sobre el texto original; las
        # líneas en blanco ni cortan ni separan la corrida.
        lines = frag.split("\n")
        pos = a
        runs: list[list[int]] = []  # [abs_start, abs_end] por corrida
        dropped = False  # hubo línea de encabezado aún sin cerrar corrida
        for ln in lines:
            lead = len(ln) - len(ln.lstrip())
            trail = len(ln.rstrip())
            s_abs, e_abs = pos + lead, pos + trail
            content = text[s_abs:e_abs]
            if not content:
                pos += len(ln) + 1
                continue  # línea en blanco: transparente
            if _HEADER_RE.match(content):
                dropped = True
                pos += len(ln) + 1
                continue
            if runs and not dropped:
                runs[-1][1] = e_abs
            else:
                runs.append([s_abs, e_abs])
                dropped = False
            pos += len(ln) + 1
        for s_abs, e_abs in runs:
            stripped = text[s_abs:e_abs]
            # Oración de una palabra o sin letras: no aporta (conservador)
            if not re.search(r"\w", stripped, re.UNICODE):
                continue
            out.append(Span(text=stripped, start=s_abs, end=e_abs))
    return out
