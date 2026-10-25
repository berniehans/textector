"""Check uniformity: dispersión de párrafos + repetición de aperturas.

Dos indicadores SEPARADOS (se reportan crudos por separado y el normalizado
es su promedio; ver docs/methodology.md):

1. q_dispersion: variabilidad de longitud de párrafos (mediana/MAD de tokens)
   como burstiness pero a escala de párrafo. Los LLM producen párrafos
   sorprendentemente parecidos entre sí.
2. q_repeticion: máxima proporción de párrafos que comparten la MISMA
   apertura de 2 tokens (contando conectores como "sin embargo", "sin duda").
   Las réplicas de diálogo empiezan con raya («—») y se cuentan aparte
   (``n_dialogo``): no participan del conteo de aperturas.

Transformación congelada F2:
- q_dispersion = clamp(1 − (cv_parrafo − 0.15) / 0.25)  # frontera AJUSTADA
  # en el gate F2 (HIGH 0.60 -> 0.40); ver docs/methodology.md §3.
- q_repeticion = clamp((share_apertura − 0.22) / 0.33)
- q = (q_dispersion + q_repeticion) / 2

Menos de ``MIN_PARRAFOS`` (3) → ``insufficient``. Determinista, sin I/O.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter

from tools.checks import CheckResult
from tools.checks.registry import register_check
from tools.scoring import PESOS
from tools.textector_core import tokenize

__all__ = ["check", "MIN_PARRAFOS", "CV_MIN", "CV_MAX", "SHARE_MIN", "SHARE_MAX"]

MIN_PARRAFOS = 3
CV_MIN = 0.15
CV_MAX = 0.40  # frontera ajustada en el gate F2 (era 0.60); docs/methodology.md §3
SHARE_MIN = 0.22
SHARE_MAX = 0.55

_PAR_SPLIT_RE = re.compile(r"\n[ \t]*\n")
_RAYA = ("—", "–")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def check(text: str) -> CheckResult:
    """Señal combinada dispersión+repetición de párrafos en [0, 1]."""
    if not isinstance(text, str):
        raise TypeError("uniformity.check espera str")
    parrafos = [p for p in _PAR_SPLIT_RE.split(text) if p.strip()]
    n = len(parrafos)
    coverage = min(1.0, n / MIN_PARRAFOS)
    if n < MIN_PARRAFOS:
        return CheckResult(
            valor_bruto={"n_paragrafos": n},
            normalizado=0.0,
            insufficient=True,
            coverage=coverage,
        )
    lens = [len(tokenize(p)) for p in parrafos]
    lens = [m for m in lens if m > 0]
    mediana = statistics.median(lens)
    mad = statistics.median(abs(x - mediana) for x in lens) if lens else 0.0
    cv = mad / mediana if mediana > 0 else 0.0
    q_dispersion = _clamp(1.0 - (cv - CV_MIN) / (CV_MAX - CV_MIN))

    prosa = [p for p in parrafos if not p.lstrip().startswith(_RAYA)]
    n_dialogo = n - len(prosa)
    # aperturas de 2 tokens; párrafos con menos de 2 tokens se cuentan como apertura corta
    aperturas: list[tuple[str, ...]] = [
        tuple(tokenize(p)[:2]) if len(tokenize(p)) >= 2 else ("<corta>",)
        for p in prosa
    ]
    if aperturas:
        c = Counter(aperturas)
        share = max(c.values()) / len(aperturas)
        q_repeticion = _clamp((share - SHARE_MIN) / (SHARE_MAX - SHARE_MIN))
        share_redondeo = round(share, 4)
    else:
        share_redondeo = None
        q_repeticion = 0.0
    q = (q_dispersion + q_repeticion) / 2.0
    bruto: dict[str, object] = {
        "n_paragrafos": n,
        "n_dialogo": n_dialogo,
        "mediana_len_parrafo": mediana,
        "cv_parrafo": round(cv, 4),
        "share_apertura_max": share_redondeo,
        "q_dispersion": round(q_dispersion, 4),
        "q_repeticion": round(q_repeticion, 4),
    }
    if not aperturas:
        bruto["sin_prosa"] = True
    return CheckResult(
        valor_bruto=bruto,
        normalizado=q,
        coverage=1.0,
        hits=[],
    )


register_check("uniformity", check, categoria="estructura", peso=PESOS["uniformity"])
