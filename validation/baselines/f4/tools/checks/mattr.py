"""Check mattr: diversidad léxica en ventana fija de 50 tokens (señal LLM-like).

Los LLM tienden a reutilizar vocabulario dentro de tramos; los humanos
muestran mayor variedad local. MATTR (Moving-Average Type-Token Ratio) con
ventana FIJA y documentada evita el sesgo de TTR global (la longitud cambia
el TTR global; con ventana fija no). Texto con menos de ``VENTANA`` tokens →
``insufficient``: NUNCA se sustituye el TTR global en silencio.

Transformación congelada F2 (docs/methodology.md):
- ventana = 50 tokens, deslizamiento = 1 token, promedio simple.
- q = clamp(1 − (mattr − 0.55) / 0.30, 0, 1)
  (mattr ≤ 0.55 → señal 1: vocabuario pobre; mattr ≥ 0.85 → 0: rico).

Determinista, sin I/O, sin red, sin azar.
"""

from __future__ import annotations

from tools.checks import CheckResult
from tools.checks.registry import register_check
from tools.scoring import PESOS
from tools.textector_core import tokenize

__all__ = ["check", "VENTANA", "MATTR_MIN", "MATTR_MAX"]

VENTANA = 50
MATTR_MIN = 0.55
MATTR_MAX = 0.85


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def check(text: str) -> CheckResult:
    """MATTR de ventana 50 en [0, 1] invertido (puro, determinista)."""
    if not isinstance(text, str):
        raise TypeError("mattr.check espera str")
    toks = tokenize(text)
    n = len(toks)
    coverage = min(1.0, n / VENTANA)
    if n < VENTANA:
        return CheckResult(
            valor_bruto={"n_tokens": n, "ventana": VENTANA},
            normalizado=0.0,
            insufficient=True,
            coverage=coverage,
        )
    ttrs = [len(set(toks[i : i + VENTANA])) / VENTANA for i in range(n - VENTANA + 1)]
    mattr = sum(ttrs) / len(ttrs)
    q = _clamp(1.0 - (mattr - MATTR_MIN) / (MATTR_MAX - MATTR_MIN))
    return CheckResult(
        valor_bruto={
            "n_tokens": n,
            "ventana": VENTANA,
            "n_ventanas": len(ttrs),
            "mattr": round(mattr, 4),
        },
        normalizado=q,
        coverage=1.0,
        hits=[f"mattr={mattr:.3f}"],
    )


register_check("mattr", check, categoria="vocabulario", peso=PESOS["mattr"])
