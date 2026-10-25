"""Contrato del perfil portable F5 y su abstención explícita."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.cli import _cargar_lexicon, _cargar_semillas
from tools.f5 import _compression_positive, puntuar
from tools.calibrate_f5 import calibrate
from tools.resources import CONFIG


LEXICON = _cargar_lexicon(CONFIG)
SEEDS = _cargar_semillas()


def sample() -> str:
    paragraph = ("La memoria de aquella ciudad parecía guardar cada invierno. "
                 "Los vecinos caminaban por calles antiguas y recordaban historias distintas. "
                 "Nadie conocía el origen de la casa junto al río, pero todos hablaban de ella. "
                 "Cada tarde cambiaba la luz y el mercado cerraba sus puertas lentamente. "
                 "La mujer volvió al jardín porque allí encontraba silencio y sombra.")
    return "\n\n".join([paragraph] * 5)


class F5PortableTests(unittest.TestCase):
    def test_indice_invariante_a_parrafos_y_mayusculas(self):
        text = sample()
        flattened = " ".join(text.lower().split())
        a = puntuar(text, LEXICON, SEEDS)
        b = puntuar(flattened, LEXICON, SEEDS)
        self.assertEqual(a["indice_llm"], b["indice_llm"])
        self.assertEqual(a["q_efectivos"], b["q_efectivos"])
        self.assertFalse(a["checks_auxiliares_fuera_del_indice"]["uniformity"]["insufficient"])
        self.assertTrue(b["checks_auxiliares_fuera_del_indice"]["uniformity"]["insufficient"])
        self.assertFalse(b["parrafos_usados_para_puntuar"])

    def test_indice_usa_denominador_fijo(self):
        result = puntuar(sample(), LEXICON, SEEDS)
        self.assertEqual(result["denominador"], 1.0)
        self.assertAlmostEqual(sum(result["pesos_fijos"].values()), 1.0)

    def test_texto_corto_abstiene_sin_renormalizar(self):
        result = puntuar("palabra " * 30, LEXICON, SEEDS)
        self.assertIsNone(result["indice_llm"])
        self.assertEqual(result["predicho"], "abstencion")
        self.assertEqual(result["denominador"], 1.0)
        self.assertIn("mattr", result["checks_insuficientes"])

    def test_un_cliche_no_satura_la_senal_lexica(self):
        text = ("en el fondo " + "palabra distinta " * 100)
        result = puntuar(text, LEXICON, SEEDS)
        contribution = result["contribuciones"]["cliches_es"]
        self.assertGreater(contribution, 0)
        self.assertLessEqual(contribution, 100 * .25 / 3)

    def test_compresion_neutral_no_aporta_contribucion(self):
        self.assertEqual(_compression_positive(0.5), 0.0)
        self.assertEqual(_compression_positive(0.25), 0.0)
        self.assertAlmostEqual(_compression_positive(0.75), 0.5)

    def test_calibrador_rechaza_corpus_reservado(self):
        reserved = Path(__file__).resolve().parents[1] / "validation/reserved-f5-v1"
        with self.assertRaisesRegex(ValueError, "solo se calibra"):
            calibrate(reserved)


if __name__ == "__main__":
    unittest.main()
