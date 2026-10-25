"""Check cliches_es: densidad de clichés IA en español con léxico YAML-min.

Port del CONCEPTO 'frases del corpus' de aifingerprint + semilla temática del
corpus MIT AIStoryHub (AStoryHub Corpus of AI Cliches, Jean-Philippe
LeBlanc, 2025): las listas EN NO se traducen literal; el léxico ES se deriva
y documenta en ``config/cliches_es.yaml`` (paso y fuente por frase).
Las señales ES nativas (perífrasis «una X que parecía...», «de quien»,
cierre «en conclusión», muletillas, «en un mundo donde...») están en el
mismo yaml marcadas ``es-nativo``.

Matching mecánico (documentado):
- Cada entrada del yaml es `"frase|peso|fuente"` (peso 0..100 estilo
  AIStoryHub; unidades efectivas = peso/10).
- ``tokenize`` casefold; matching de SECUENCIA CONTIGUA de tokens exactos,
  con comodín ``__`` que coincide con EXACTAMENTE UN token cualquiera.
- Ventana deslizante; los solapamientos se consumen de izquierda a
  derecha (greedy, no ambiguo).
- Densidad ponderada = Σ(unidades·n_hits) · 1000 / n_tokens.
- q = clamp(densidad / Q_DENSIDAD_MAXIMA) (congelado en 2.5).

La salida es ANONIMIZADA: los hits citan posición de token y conteo, nunca
el fragmento de texto crudo (ver límites del proyecto). Con menos de
``MIN_TOKENS`` tokens → ``insufficient``. Sin I/O: el yaml LO CARGA quien orquesta
(``phrases_from_parsed``/``load_lexicon``) — y este check recibe el léxico
ya parseado (o usa el mínimo embebido determinista). Decision de diseño:
el check nunca aplica I/O; el archivo lo abre quien orquesta.
"""

from __future__ import annotations

from typing import Iterable

from tools.checks import CheckResult
from tools.checks.registry import register_check
from tools.lexicon import parse_yaml_min
from tools.scoring import PESOS
from tools.textector_core import tokenize

__all__ = [
    "ClicheEntry",
    "decode_entries",
    "build_lexicon",
    "phrases_from_parsed",
    "load_lexicon",
    "check",
    "SEMILLA_YAML_MIN",
    "MIN_TOKENS",
    "Q_DENSIDAD_MAXIMA",
]

MIN_TOKENS = 50
Q_DENSIDAD_MAXIMA = 2.5

_COMODIN = "__"
# El tokenizador descarta guiones bajos ([^\W_]+), así que el comodín "__"
# se reemplaza por un centinela deliberadamente improbable antes de tokenizar.
_SENTINEL_COMODIN = "qzcomodinqz"


class ClicheEntry:
    """Entrada decodificada del léxico (tokens casefold, peso en unidades 0..10)."""

    __slots__ = ("idx", "tokens", "peso_units", "peso_raw", "fuente", "frase_cruda")

    def __init__(
        self, idx: int, tokens: tuple[str, ...], peso_raw: float, fuente: str,
        frase_cruda: str,
    ):
        self.idx = idx
        self.tokens = tokens
        self.peso_raw = peso_raw
        self.peso_units = peso_raw / 10.0
        self.fuente = fuente
        self.frase_cruda = frase_cruda

    def __repr__(self) -> str:  # sin texto crudo: solo metadatos
        return (
            f"ClicheEntry(id={self.idx}, pesos={self.peso_raw}, "
            f"fuente={self.fuente!r}, n_tokens={len(self.tokens)})"
        )


def _frase_valida(frase: str):  # -> tuple[str, ...] | None (comodín)
    toks = tuple(tokenize(frase.replace(_COMODIN, " " + _SENTINEL_COMODIN + " ")))
    if not toks:
        raise ValueError(f"frase vacía tras tokenizar: {frase!r}")
    for t in toks:
        if t == _SENTINEL_COMODIN:
            continue
        if not (t.isalpha() and all(c.isalpha() for c in t)):
            raise ValueError(f"token inválido en frase: {t!r} (frase {frase!r})")
    if _SENTINEL_COMODIN in toks and len(toks) < 3:
        raise ValueError("los patrones con comodín requieren contexto ancla (>=3 tokens)")
    return toks


def decode_entries(scalares: Iterable[str]) -> list[ClicheEntry]:
    """Mapea ``['frase|peso|fuente', ...]`` a entradas tipadas; error en mal formato."""
    entries: list[ClicheEntry] = []
    for idx, scalar in enumerate(scalares):
        if not isinstance(scalar, str):
            raise ValueError(f"entrada {idx}: debe ser str")
        partes = scalar.split("|")
        if len(partes) != 3:
            raise ValueError(
                f"entrada {idx}: se esperaba 'frase|peso|fuente', "
                f"llegaron {len(partes)} partes"
            )
        frase, peso_crudo, fuente = (p.strip() for p in partes)
        if not frase:
            raise ValueError(f"entrada {idx}: frase vacía")
        try:
            peso = float(peso_crudo)
        except ValueError as e:
            raise ValueError(f"entrada {idx}: peso no numérico {peso_crudo!r}") from e
        if not (0.0 <= peso <= 100.0):
            raise ValueError(f"entrada {idx}: peso fuera de [0, 100]: {peso}")
        if not fuente:
            raise ValueError(f"entrada {idx}: fuente vacía")
        entries.append(ClicheEntry(idx, _frase_valida(frase), peso, fuente, frase))
    return entries


def phrases_from_parsed(parsed: dict[str, object]) -> list[ClicheEntry]:
    """Extrae las entradas desde el dict del ``parse_yaml_min``."""
    escalares: list[str] = []
    if "cliches" in parsed and isinstance(parsed["cliches"], list):
        escalares.extend(t for t in parsed["cliches"] if isinstance(t, str))
    if not escalares and "phrases" in parsed and isinstance(parsed["phrases"], list):
        escalares.extend(t for t in parsed["phrases"] if isinstance(t, str))
    return decode_entries(escalares)


def load_lexicon(yaml_text: str) -> list[ClicheEntry]:
    """Carga el léxico desde el TEXTO del yaml (sin I/O por decisión del caller)."""
    return phrases_from_parsed(parse_yaml_min(yaml_text))


def build_lexicon() -> list[ClicheEntry]:
    """Léxico mínimo EMBEBIDO determinista (fuente: SEMILLA_YAML_MIN)."""
    return load_lexicon(SEMILLA_YAML_MIN)


# Léxico mínimo embebido (mismo formato YAML-min). La FUENTE DE LA VERDAD
# COMPLETA es config/cliches_es.yaml (cargada por el CLI en F4).
SEMILLA_YAML_MIN = """\
version: 1

cliches:
  - "en conclusión|40|es-nativo"
  - "no es solo __, es __|35|es-nativo"
  - "una __ que parecía|30|es-nativo"
"""


def _coincide(patron: tuple[str, ...], toks: list[str]) -> list[tuple[int, int]]:
    """Igualdad exacta contiguo a contiguo; ``__`` coincide con UN token."""
    n_pat = len(patron)
    salidas: list[tuple[int, int]] = []
    i = 0
    while i <= len(toks) - n_pat:
        ok = True
        for j, p in enumerate(patron):
            tok = toks[i + j]
            if p != _SENTINEL_COMODIN and p != tok:
                ok = False
                break
        if ok:
            salidas.append((i, i + n_pat))
            i += n_pat
        else:
            i += 1
    return salidas


def check(text: str, *, lexicon: list[ClicheEntry] | None = None) -> CheckResult:
    """Densidad ponderada de clichés en [0, 1]; salida anonimizada."""
    if not isinstance(text, str):
        raise TypeError("cliches_es.check espera str")
    if lexicon is None:
        lexicon = build_lexicon()
    toks = tokenize(text)
    n = len(toks)
    coverage = min(1.0, n / MIN_TOKENS)
    if n < MIN_TOKENS:
        return CheckResult(
            valor_bruto={"n_tokens": n},
            normalizado=0.0,
            insufficient=True,
            coverage=coverage,
        )
    hit_records: list[dict[str, object]] = []
    por_id: list[tuple[ClicheEntry, int]] = []
    total_unidades = 0.0
    for entrada in lexicon:
        matches = _coincide(entrada.tokens, toks)
        if not matches:
            continue
        por_id.append((entrada, len(matches)))
        total_unidades += entrada.peso_units * len(matches)
        for (ini, fin) in matches:
            hit_records.append({"id": entrada.idx, "pos": ini, "fin": fin})
    densidad = total_unidades * 1000.0 / n
    q = min(1.0, densidad / Q_DENSIDAD_MAXIMA)
    por_cliche = [
        {"id": e.idx, "conteo": c, "peso": e.peso_raw, "fuente": e.fuente}
        for (e, c) in por_id
    ]
    return CheckResult(
        valor_bruto={
            "n_tokens": n,
            "n_hits_total": len(hit_records),
            "densidad_ponderada_por_1000": round(densidad, 4),
            "unidades_totales": round(total_unidades, 4),
            "por_cliche": por_cliche,
        },
        normalizado=q,
        coverage=1.0,
        hits=[
            {"id": h["id"], "pos": h["pos"], "fin": h["fin"]} for h in hit_records
        ][:200],  # tope de lista para reportes grandes (resto agregado en bruto)
    )


register_check("cliches_es", check, categoria="léxico", peso=PESOS["cliches_es"])
