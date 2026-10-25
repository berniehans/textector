"""Check burstiness: variabilidad de longitud de oraciones (señal LLM-like).

Mecanismo por densidad (port del concepto de ``checks/burstiness.py`` de
aifingerprint 1.6.0, auditoría en docs/audit_aifingerprint.md): los LLM
tienden a oraciones de longitud parecida; los humanos alternan. Medimos con
**mediana/MAD** (robusto) en vez del CV clásico: extremos (elipsis, réplicas)
no mandan sobre la señal.

Transformación congelada F2 (docs/methodology.md):
- cv_robusto = MAD(longitudes) / mediana(longitudes), longitudes en tokens.
- q = clamp(1 − (cv_robusto − 0.20) / 0.40, 0, 1)
  (cv ≤ 0.20 → señal 1: uniformidad máxima; cv ≥ 0.60 → 0: variado).

Menos de ``MIN_ORACIONES`` (10) → ``insufficient`` (sin señal silenciosa).
Determinista, sin I/O, sin red, sin azar.
"""

from __future__ import annotations

import statistics

from tools.checks import CheckResult
from tools.checks.registry import register_check
from tools.scoring import PESOS
from tools.textector_core import split_sentences, tokenize

__all__ = ["check", "MIN_ORACIONES", "CV_MIN", "CV_MAX"]

MIN_ORACIONES = 10
CV_MIN = 0.20
CV_MAX = 0.60


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def check(text: str) -> CheckResult:
    """Señal de uniformidad rítmica de oraciones en [0, 1] (pura, determinista)."""
    if not isinstance(text, str):
        raise TypeError("burstiness.check espera str")
    spans = split_sentences(text)
    longitudes = [len(tokenize(s.text)) for s in spans]
    longitudes = [n for n in longitudes if n > 0]
    n = len(longitudes)
    coverage = min(1.0, n / MIN_ORACIONES)
    n_dialogo = sum(1 for s in spans if s.text.lstrip().startswith(("—", "–")))
    if n < MIN_ORACIONES:
        return CheckResult(
            valor_bruto={"n_oraciones": n, "n_dialogo": n_dialogo},
            normalizado=0.0,
            insufficient=True,
            coverage=coverage,
        )
    mediana = statistics.median(longitudes)
    mad = statistics.median(abs(x - mediana) for x in longitudes)
    cv_robusto = mad / mediana if mediana > 0 else 0.0
    q = _clamp(1.0 - (cv_robusto - CV_MIN) / (CV_MAX - CV_MIN))
    return CheckResult(
        valor_bruto={
            "n_oraciones": n,
            "n_dialogo": n_dialogo,
            "mediana_len": mediana,
            "mad_len": mad,
            "cv_robusto": round(cv_robusto, 4),
        },
        normalizado=q,
        coverage=coverage,
        hits=[f"cv_robusto={cv_robusto:.3f}"],
    )


register_check("burstiness", check, categoria="ritmo", peso=PESOS["burstiness"])
