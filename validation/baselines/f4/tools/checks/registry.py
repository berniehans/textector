"""Registro de checks de textector.

Contrato (firma común) portado del referencial aifingerprint 1.6.0, cuyo
``checks/__init__.py`` dicta ``CheckResult = tuple[list[str], float]`` y el
``analyzer.py`` suma ``raw_score * CATEGORY_WEIGHTS[name]`` acotando a [0,100]
(ver docs/audit_aifingerprint.md). Todo check registrado expone el mismo
esqueleto de resultado:

    valor_bruto      -> hallazgos en crudo (hits, métricas)
    normalizado      -> señal en [0.0, 1.0]
    peso             -> peso de la categoría (F2/F3, calibración)
    contribucion     -> normalizado * peso (acotado en el agregador)
    coverage         -> fracción de texto evaluada ([0.0, 1.0])
    insufficient     -> True si el check no corrió por falta de datos

En F1 el registro está vacío a propósito: los checks concretos llegan en F2
(desde el port de aifingerprint) y sus pesos en F3 (calibración con corpus).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from tools.checks import CheckResult

__all__ = ["CheckFunc", "CheckEntry", "list_checks", "register_check", "get_check"]

#: Todos los checks comparten la misma firma de función.
CheckFunc = Callable[..., CheckResult]


@dataclass(frozen=True)
class CheckEntry:
    """Una entrada del registro: id estable + función + metadata del check."""

    name: str
    check: CheckFunc
    categoria: str
    peso: float = 0.0  # asignado en F3 (calibración); 0.0 en F1/F2
    coverage: float = 1.0
    valor_bruto: dict[str, Any] = field(default_factory=dict)
    contribucion: float = 0.0
    insufficient: bool = False
    version: str = "1"


_REGISTRY: dict[str, CheckEntry] = {}


def register_check(
    name: str, check: CheckFunc, categoria: str, peso: float = 0.0
) -> CheckEntry:
    """Registra un check con la firma común. Rechaza duplicados (fail-closed)."""
    if not isinstance(name, str) or not name:
        raise ValueError("register_check exige un name no vacío")
    if name in _REGISTRY:
        raise ValueError(f"check duplicado en el registro: {name!r}")
    entry = CheckEntry(name=name, check=check, categoria=categoria, peso=peso)
    _REGISTRY[name] = entry
    return entry


def list_checks() -> list[CheckEntry]:
    """Lista estable (por nombre) del registro. Vacía en F1 por diseño."""
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def get_check(name: str) -> CheckEntry:
    """Obtiene un check por name; KeyError con mensaje claro si no existe."""
    if name not in _REGISTRY:
        raise KeyError(f"check no registrado: {name!r}")
    return _REGISTRY[name]
