"""Parser YAML-min del léxico de textector (F2): pequeño, fail-closed.

Spec congelada por ``tests/test_yaml_lexicon.py`` (escrita en F1):
- ``version: <entero>`` a nivel raíz (obligatorio).
- Listas planas de escalares double-quoted (estilo JSON), un elemento por
  línea ``- \"...\"``. Cualquier clave raíz puede llevar lista; textector usa
  ``phrases`` (legacy del esqueleto F1, vacía) y ``cliches`` (poblada en F2),
  ver docs/methodology.md y config/cliches_es.yaml.
- Líneas en blanco y comentarios de LÍNEA COMPLETA (la línea empieza con
  ``#`` después de espacios) son transparentes.

RECHAZA con ``MarkerError`` (mensaje claro):
- tags (``!!int``), alias (``*a``) y anclas (``&a``),
- estructuras anidadas (``- clave: valor``),
- escalares multilínea/bloques (``|``, ``>``, comilla sin cerrar en la línea),
- comentarios inline (``#`` tras el valor),
- claves duplicadas,
- valor no entero en ``version`` / ``version`` ausente.

Sin I/O, sin red, determinista.
"""

from __future__ import annotations

import re

__all__ = ["MarkerError", "parse_yaml_min"]


class MarkerError(ValueError):
    """Error de formato YAML-min: el parser es fail-closed."""


_ITEM_RE = re.compile(r'^\s*-\s"((?:\\.|[^"\\])*)"\s*$')
_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
_INT_RE = re.compile(r"^[0-9]+$")

_ESCAPE_SIMPLE = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r", "/": "/"}


def _unescape(crudo: str, linea: int) -> str:
    """Desescapa un escalar double-quoted estilo JSON (\\\" \\\\ \\n \\t \\uXXXX)."""
    out: list[str] = []
    i = 0
    while i < len(crudo):
        ch = crudo[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(crudo):
            raise MarkerError(f"línea {linea}: escape incompleto en escalar double-quoted")
        e = crudo[i]
        if e in _ESCAPE_SIMPLE:
            out.append(_ESCAPE_SIMPLE[e])
            i += 1
        elif e == "u":
            hexa = crudo[i + 1 : i + 5]
            if len(hexa) != 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hexa):
                raise MarkerError(f"línea {linea}: escape \\u inválido")
            out.append(chr(int(hexa, 16)))
            i += 5
        else:
            raise MarkerError(f"línea {linea}: escape desconocido \\{e}")
    return "".join(out)


def _error_lista(linea: int, content: str) -> MarkerError:
    """Error claro para un elemento de lista que no es escalar double-quoted."""
    if content.startswith("|") or content.startswith(">"):
        return MarkerError(f"línea {linea}: bloque multilínea no soportado (multilínea)")
    if content.startswith('"'):
        # escalar quoted que no cerró en la línea: multilínea (fail-closed)
        return MarkerError(
            f"línea {linea}: escalar double-quoted sin cerrar en la misma línea "
            "(multilínea)"
        )
    if ":" in content:
        return MarkerError(f"línea {linea}: estructura anidada no soportada (anidado)")
    if "*" in content:
        return MarkerError(f"línea {linea}: alias/ancla no soportada (alias)")
    if "&" in content:
        return MarkerError(f"línea {linea}: alias/ancla no soportada (ancla-alias)")
    if "!" in content:
        return MarkerError(f"línea {linea}: tag no soportado (tag)")
    if "#" in content:
        return MarkerError(f"línea {linea}: comentario inline no soportado (inline)")
    return MarkerError(
        f"línea {linea}: elemento de lista debe ser escalar double-quoted "
        "(estilo JSON '- \"...\"')"
    )


def parse_yaml_min(text: str) -> dict[str, object]:
    """Parsea YAML-min y devuelve ``{"version": int, "<clave>": [str, ...], ...}``."""
    if not isinstance(text, str):
        raise TypeError("parse_yaml_min espera str")
    resultado: dict[str, object] = {}
    current: str | None = None
    for idx, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue  # línea en blanco: transparente
        if stripped.startswith("#"):
            continue  # comentario de línea completa: transparente

        m_item = _ITEM_RE.match(raw)
        if m_item:
            if current is None:
                raise MarkerError(f"línea {idx}: elemento de lista sin clave previa")
            valor = _unescape(m_item.group(1), idx)
            resultado[current].append(valor)  # type: ignore[union-attr]
            continue

        m_key = _KEY_RE.match(stripped)
        if m_key is None:
            if stripped.startswith("- "):
                raise _error_lista(idx, stripped[2:].strip())
            raise MarkerError(f"línea {idx}: línea no reconocida por YAML-min")
        if raw != raw.lstrip():
            # clave indentada = estructura anidada (fail-closed)
            raise MarkerError(f"línea {idx}: estructura anidada no soportada (anidado)")

        clave, valor_crudo = m_key.group(1), m_key.group(2).strip()
        if clave in resultado:
            raise MarkerError(f"línea {idx}: clave duplicada: {clave!r}")
        if valor_crudo == "":
            resultado[clave] = []
            current = clave  # la lista llega como líneas '- "..."'
            continue
        current = None
        if valor_crudo in ("[]", "[ ]"):
            resultado[clave] = []
            continue
        if "#" in valor_crudo:
            raise MarkerError(f"línea {idx}: comentario inline no soportado (inline)")
        if _INT_RE.match(valor_crudo):
            resultado[clave] = int(valor_crudo)
            continue
        if valor_crudo.startswith("!"):
            raise MarkerError(f"línea {idx}: tag no soportado (tag)")
        if "*" in valor_crudo:
            raise MarkerError(f"línea {idx}: alias/ancla no soportada (alias)")
        if "&" in valor_crudo:
            raise MarkerError(f"línea {idx}: alias/ancla no soportada (ancla-alias)")
        if valor_crudo.startswith("|") or valor_crudo.startswith(">"):
            raise MarkerError(f"línea {idx}: bloque multilínea no soportado (multilínea)")
        if clave not in ("version", "phrases", "cliches"):
            raise MarkerError(f"línea {idx}: clave de raíz no permitida: {clave!r}")
        raise MarkerError(
            f"línea {idx}: valor debe ser entero, lista vacía o lista de escalares "
            f"double-quoted: {valor_crudo!r}"
        )

    if "version" not in resultado:
        raise MarkerError("falta la clave 'version' (entero) a nivel raíz")
    if not isinstance(resultado["version"], int) or isinstance(
        resultado["version"], bool
    ):
        raise MarkerError("'version' debe ser un entero")
    return resultado
