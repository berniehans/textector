"""Especificación ejecutable del parser YAML-min del léxico (cliches_es.yaml).

El parser llega en F2 (``tools/lexicon.py``, módulo ``parse_yaml_min``).
Estos tests se escriben AHORA como spec de F1 y quedan en *skip* (no en
fallo) mientras el módulo no exista, para que la suite de F1 esté verde.

Formato soportado (fail-closed):
- ``version: <entero>`` a nivel raíz.
- ``phrases:`` seguido de lista de escalares double-quoted (estilo JSON),
  un elemento por línea ``- "..."``.
- Líneas en blanco y comentarios de línea completa (# al inicio).
RECHAZA (con error claro): tags, alias/anclas, estructuras anidadas (mapas
dentro de listas), escalares multilínea/bloques, comentarios inline y claves
duplicadas.
"""

from __future__ import annotations

import unittest

try:  # el parser llega en F2
    from tools.lexicon import MarkerError, parse_yaml_min  # type: ignore

    _LEXICON_OK = True
except ModuleNotFoundError:  # estado F1: parser pendiente
    MarkerError = Exception  # type: ignore[misc,assignment]
    parse_yaml_min = None  # type: ignore[assignment]
    _LEXICON_OK = False

VALID = """\
# sectores de léxico
version: 1

phrases:
  - "en el mundo de"
  - "sum\u00e9rgete en"
  - "no es solo \\\"x\\\", es \\\"y\\\""
"""


@unittest.skipUnless(_LEXICON_OK, "parser YAML-min llega en F2 (tools/lexicon.py)")
class TestParserValido(unittest.TestCase):
    def test_valido_con_acentos_y_comillas_escapadas(self):
        result = parse_yaml_min(VALID)
        self.assertEqual(result["version"], 1)
        self.assertEqual(
            result["phrases"],
            ["en el mundo de", "sum\u00e9rgete en", 'no es solo "x", es "y"'],
        )

    def test_config_real_parsea(self):
        from pathlib import Path

        cfg = Path(__file__).resolve().parent.parent / "config" / "cliches_es.yaml"
        result = parse_yaml_min(cfg.read_text(encoding="utf-8"))
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["phrases"], [])


@unittest.skipUnless(_LEXICON_OK, "parser YAML-min llega en F2 (tools/lexicon.py)")
class TestParserRechazos(unittest.TestCase):
    def _rechaza(self, text: str, detalle: str):
        with self.assertRaises(MarkerError) as ctx:
            parse_yaml_min(text)
        self.assertIn(detalle, str(ctx.exception).lower())

    def test_tag(self):
        self._rechaza("version: !!int 1\n", "tag")

    def test_alias_y_ancla(self):
        self._rechaza("base: &a 1\nversion: *a\n", "alias")
        self._rechaza("base: &a 1\nversion: &b *a\n", "ancla")

    def test_anidado(self):
        self._rechaza("phrases:\n  - clave: \"valor\"\n", "anidado")

    def test_multilinea(self):
        self._rechaza("phrases:\n  - |\n    bloque\n", "multil")
        self._rechaza('phrases:\n  - "texto\n    cortado"\n', "multil")

    def test_comentario_inline(self):
        self._rechaza("version: 1  # comentario del final\n", "inline")

    def test_duplicado(self):
        self._rechaza("version: 1\nversion: 2\n", "duplic")


if __name__ == "__main__":
    unittest.main()
