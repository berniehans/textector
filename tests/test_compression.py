"""Tests F2 del check de compresión (método zippy redefinido, semilla sintética).

En F2 la semilla es una fixture sintética determinista empaquetada en el
propio módulo (las semillas ES reales llegan en F3, solo del subconjunto IA
de train). Estos tests validan el MECANISMO (delta con signo, normalización
por bytes, determinismo, abstención), no el desempeño real.
"""

from __future__ import annotations

import unittest

from tools.checks import compression
from tools.textector_core import tokenize


class TestSemillasSinteticas(unittest.TestCase):
    def test_semillas_deterministas_y_suficientes(self):
        s1 = compression.semilla_ia()
        s2 = compression.semilla_humana()
        self.assertEqual(s1, compression.semilla_ia())  # determinista
        self.assertEqual(s2, compression.semilla_humana())
        self.assertGreater(len(s1.encode("utf-8")), 1500)
        self.assertGreater(len(s2.encode("utf-8")), 1500)

    def test_semillas_distintas(self):
        self.assertNotEqual(compression.semilla_ia(), compression.semilla_humana())


class TestCompression(unittest.TestCase):
    def _muestra_ia(self) -> str:
        return " ".join(compression.semilla_ia().split()[:400])

    def _muestra_humano(self) -> str:
        return " ".join(compression.semilla_humana().split()[:400])

    def test_determinista(self):
        r1 = compression.check(self._muestra_ia())
        r2 = compression.check(self._muestra_ia())
        self.assertEqual(r1, r2)

    def test_muestras_ia_vs_humano_separadas(self):
        q_ia = compression.check(self._muestra_ia()).normalizado
        q_h = compression.check(self._muestra_humano()).normalizado
        self.assertGreater(q_ia, q_h + 0.10)  # delta_ia < delta_h en la IA
        self.assertGreaterEqual(q_ia, 0.5)
        self.assertLessEqual(q_h, 0.5)

    def test_invariante_direccional_al_duplicar(self):
        """Invariante CORRECTO según el plan F2: la direcciÓn, no el valor.

        Al duplicar la muestra, delta y q NO son invariantes (deflate
        re-consume redundancia; ~0.16 en q al x2 con esta fixture). Lo que
        el plan garantiza es el lado del umbral 0.5 (corte IA); el valor
        exacto del corte se fija por train en F3 (docs/methodology.md §3/§5).
        """
        m = self._muestra_ia()
        q1 = compression.check(m).normalizado
        q2 = compression.check(m + " " + m).normalizado
        self.assertGreater(q1, 0.5)
        self.assertGreater(q2, 0.5)

    def test_insuficiente_texto_muy_corto(self):
        res = compression.check(" ".join(tokenize("Mesas río y sol.")))
        self.assertTrue(res.insufficient)
        self.assertEqual(res.normalizado, 0.0)
        self.assertLess(res.coverage, 1.0)

    def test_tabla_de_valores_explicables(self):
        res = compression.check(self._muestra_humano())
        vb = res.valor_bruto
        self.assertIn("m_ia", vb)
        self.assertIn("m_h", vb)
        self.assertIn("nivel", vb)
        self.assertGreater(vb["n_seed_ia"], 0)
        self.assertGreater(vb["n_seed_h"], 0)
        # marginales calibrados por bytes de la muestra
        self.assertGreater(vb["m_h"], 0.0)

    def test_coverage_completo_en_texto_normal(self):
        res = compression.check(self._muestra_ia())
        self.assertAlmostEqual(res.coverage, 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
