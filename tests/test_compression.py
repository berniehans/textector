"""Tests F2/F5 del check de compresión (método zippy redefinido, semillas).

En F2 la semilla era una fixture sintética determinista empaquetada en el
propio módulo. Desde F5 el check acepta semillas ES reales inyectadas como
str (``seed_ia=``/``seed_hum=``, ambas o ninguna). Estos tests validan el
MECANISMO (delta con signo, normalización por bytes, determinismo,
abstención) y el wiring de semillas (etiqueta + trazabilidad sha256), no el
desempeño real.
"""

from __future__ import annotations

import hashlib
import inspect
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


# -----------------------------------------------------------------------------
# F5.2: semillas ES reales inyectadas (enmienda 4). El check sigue puro:
# las semillas entran como str crudos, sin I/O ni rutas.
# -----------------------------------------------------------------------------

_MUESTRA = " ".join(compression.semilla_ia().split()[:400])
_SEED_IA = (
    "La memoria avanza hacia el borde del barrio y el eco se queda como "
    "sombra antigua del tiempo. "
) * 40
_SEED_HUM = (
    "Río penumbra llave chispa rincón barro cariño mediodía escoba sirena "
    "brisa azotea sardina garbanzo termo ardilla. —No sé. "
) * 40


class TestSemillasRealesInyectadas(unittest.TestCase):
    """F5.2: inyección de semillas reales, trazabilidad y pureza."""

    def test_check_con_semillas_inyectadas_reporta_reales_es(self):
        res = compression.check(_MUESTRA, seed_ia=_SEED_IA, seed_hum=_SEED_HUM)
        self.assertEqual(res.valor_bruto["semillas"], "reales-es")
        self.assertEqual(
            res.valor_bruto["sha256_seed_ia"],
            hashlib.sha256(_SEED_IA.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            res.valor_bruto["sha256_seed_hum"],
            hashlib.sha256(_SEED_HUM.encode("utf-8")).hexdigest(),
        )

    def test_check_sin_semillas_mantiene_sinteticas_f2(self):
        res = compression.check(_MUESTRA)
        self.assertEqual(res.valor_bruto["semillas"], "sinteticas-f2")
        self.assertNotIn("sha256_seed_ia", res.valor_bruto)
        self.assertNotIn("sha256_seed_hum", res.valor_bruto)

    def test_check_determinista_con_semillas_reales(self):
        r1 = compression.check(_MUESTRA, seed_ia=_SEED_IA, seed_hum=_SEED_HUM)
        r2 = compression.check(_MUESTRA, seed_ia=_SEED_IA, seed_hum=_SEED_HUM)
        self.assertEqual(r1.normalizado, r2.normalizado)
        self.assertEqual(r1.valor_bruto, r2.valor_bruto)
        self.assertEqual(r1.hits, r2.hits)

    def test_check_inyeccion_mixta_rechazada(self):
        """Extra (fuera de los 11 del plan): inyección parcial es fail-closed.

        Una sola semilla inyectada mezclaría real con sintética bajo una
        etiqueta única: se rechaza en lugar de reportar algo ambiguo.
        """
        with self.assertRaises(ValueError):
            compression.check(_MUESTRA, seed_ia=_SEED_IA)
        with self.assertRaises(ValueError):
            compression.check(_MUESTRA, seed_hum=_SEED_HUM)
        with self.assertRaises(TypeError):
            compression.check(_MUESTRA, seed_ia=123, seed_hum=_SEED_HUM)

    def test_check_no_lee_disco(self):
        # El módulo no contiene primitivas de I/O y trabaja con str puros
        # sin rutas: la carga de semillas es del orquestador (CLI/calibrate).
        fuente = inspect.getsource(compression)
        self.assertNotIn("open(", fuente)
        self.assertNotIn("pathlib", fuente)
        self.assertNotIn("Path(", fuente)
        res = compression.check(_MUESTRA, seed_ia=_SEED_IA, seed_hum=_SEED_HUM)
        self.assertFalse(res.insufficient)


if __name__ == "__main__":
    unittest.main()
