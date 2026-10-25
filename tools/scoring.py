"""Scoring explicable F2: pesos congelados, topes de grupo, renormalización.

Contrato (porta el esquema de ``analyzer.py`` de aifingerprint 1.6.0,
auditoría en docs/audit_aifingerprint.md):

    contribucion_i = 100 · w_i · q_i / Σ w_disponibles
    indice_llm     = int(round(Σ contribuciones)) ∈ [0, 100]

- ``q_i`` es el ``normalizado`` del CheckResult acotado a [0, 1].
- Solo participan los checks disponibles (``insufficient=False``); los
  pesos se renormalizan ÚNICAMENTE entre disponibles.
- Tope de peso CONJUNTO para grupo de checks con señal correlacionada
  (ver docs/methodology.md): si Σw del grupo excede el tope, el grupo se
  reescala proporcionalmente.
- Reporte determinista y con claves ordenadas; JSON via ``json.dumps
  (sort_keys=True)``. Sin azar, sin red, sin I/O.

Los PESOS y TOPES están CONGELADOS en F2 (F3 calibra umbrales con corpus,
no los pesos; ver docs/methodology.md).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["PESOS", "TOPES_GRUPO", "VERSION_METODO", "compute_indice"]

if TYPE_CHECKING:  # pragma: no cover
    from tools.checks import CheckResult

VERSION_METODO = "f4-integridad"

#: Pesos de categoría CONGELADOS en F2 (transformaciones en cada check).
PESOS: dict[str, float] = {
    "burstiness": 0.18,
    "mattr": 0.17,
    "uniformity": 0.18,
    "cliches_es": 0.24,
    "compression": 0.23,
}

#: (grupo correlacionado, tope de peso conjunto)
TOPES_GRUPO: tuple[tuple[tuple[str, str], float], ...] = (
    (("mattr", "burstiness"), 0.32),
    (("cliches_es", "uniformity"), 0.40),
)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


class _ResultadoJSON(dict):
    """dict JSON-nativo y serializable que conserva acceso por atributo.

    Contrato del informe (test DeterminismoYOrden): json.dumps debe
    serializar todo el informe sin tipos de dataclass. Dict puro rompería
    el acceso por atributo (``resultado[m].contribucion`` en test_scoring
    verde), así que el informe expone esta subclase de dict: json.dumps la
    serializa exactamente como dict; en el proceso se lee por atributo como
    CheckResult.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _resultado_a_json(
    r: "CheckResult", peso: float, contribucion: float
) -> _ResultadoJSON:
    """Convierte CheckResult (+ peso/contribución acoplados) a JSON-nativo."""
    return _ResultadoJSON(
        valor_bruto=dict(r.valor_bruto),
        normalizado=float(r.normalizado),
        peso=float(peso),
        contribucion=float(contribucion),
        coverage=float(r.coverage),
        insufficient=bool(r.insufficient),
        hits=list(r.hits),
    )


def compute_indice(results: dict[str, "CheckResult"]) -> dict[str, Any]:
    """Calcula el índice explicable desde los CheckResult disponibles.

    Devuelve un dict determinista con claves ordenadas: ``indice_llm``
    (entero o None si nada corrió), ``suma_contribuciones`` (flotante exacta),
    ``pesos`` (ya con topes aplicados), ``contribuciones``,
    ``resultado`` (dict JSON-nativo por check, peso/contribución
    acoplados; acceso por atributo en proceso, serializable con
    json.dumps), ``insufficient_text`` y ``version``.
    """
    if not isinstance(results, dict):
        raise TypeError("compute_indice espera dict[str, CheckResult]")
    disponibles = {n: r for n, r in sorted(results.items()) if not r.insufficient}
    base: dict[str, Any] = {
        "indice_llm": None,
        "insufficient_text": True,
        "pesos": {},
        "contribuciones": {},
        "resultado": {},
        "version": VERSION_METODO,
    }
    base["suma_contribuciones"] = 0.0
    base["n_disponibles"] = 0
    if not disponibles:
        return base
    faltan = set(disponibles) - set(PESOS)
    if faltan:
        raise ValueError(
            "checks sin peso congelado en scoring.PESOS: " + ", ".join(sorted(faltan))
        )
    pesos = {n: PESOS[n] for n in disponibles}
    for (a, b), tope in TOPES_GRUPO:
        if a in pesos and b in pesos:
            suma_grupo = pesos[a] + pesos[b]
            if suma_grupo > tope:
                factor = tope / suma_grupo
                pesos[a] *= factor
                pesos[b] *= factor
    suma = sum(pesos.values())
    contribuciones = {
        n: 100.0 * pesos[n] * _clamp(r.normalizado) / suma
        for n, r in disponibles.items()
    }
    resultados_json = {
        n: _resultado_a_json(r, pesos[n], contribuciones[n])
        for n, r in disponibles.items()
    }
    suma_contrib = float(sum(contribuciones.values()))
    return {
        "indice_llm": int(round(suma_contrib)),
        "insufficient_text": False,
        "suma_contribuciones": suma_contrib,
        "pesos": pesos,
        "contribuciones": contribuciones,
        "resultado": resultados_json,
        "n_disponibles": len(disponibles),
        "version": VERSION_METODO,
    }
