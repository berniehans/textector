"""Contrato de checks de textector: CheckResult + protocolo Check.

Se porta el CONTRATO del referencial (aifingerprint 1.6.0):
``checks/__init__.py`` usa CheckResult = (hits, raw) y cada check es una
función ``check(text, lines) -> (hits, raw)``, sin estado y sin I/O.

textector formaliza ese contrato en un Protocol tipado y añade los campos de
explicabilidad que el análisis requiere: peso de la categoría, contribución
ponderada y cobertura mínima de texto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

__all__ = ["Check", "CheckResult"]


@dataclass(frozen=True)
class CheckResult:
    """Salida normalizada de un check, diseñada para el reporte explicable.

    - valor_bruto: dict con los hallazgos en crudo del check
      (por ejemplo ``{"hits": [...], "raw": 0.42}`` o métricas propias).
    - normalizado: señal del check en [0.0, 1.0] (0 = sin señal, 1 = máxima).
    - peso: peso de la categoría en el índice (definido en calibration F2/F3).
    - contribucion: ``normalizado * peso``; el índice es la suma acotada a [0, 100].
    - coverage: fracción del texto que el check pudo evaluar (longitud,
      número de oraciones, etc.); < ``MIN_COVERAGE`` ⇒ insuficiente.
    - insufficient: True cuando el check no corre por falta de datos
      (texto corto, pocas oraciones...). Un check insuficiente NO aporta
      contribución al índice.
    """

    valor_bruto: dict[str, Any]
    normalizado: float = 0.0
    peso: float = 0.0
    contribucion: float = 0.0
    coverage: float = 0.0
    insufficient: bool = False
    hits: list[str | dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class Check(Protocol):
    """Firma común de todo check: puro, sin I/O, determinista.

    ``check(valor_bruto, normalizado) -> CheckResult`` es la vista del
    análisis; la función del check recibe el texto preprocesado y produce
    el resultado al que el runner le acopla peso/contribución/coverage.
    Lista concreta de checks: llega en F2 (el registro inicia vacío).
    """

    def __call__(self, text: str) -> CheckResult: ...
