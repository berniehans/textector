"""Tests F2 del scoring explicable: pesos congelados, tope conjunto, renormalización.

Contrato: contribucion = 100·w·q/Σw_disponibles; score entero 0..100 =
suma de contribuciones (coherencia salvo redondeo declarado). Los pesos y
los topes de grupo son CONGELADOS en F2 (docs/methodology.md).
"""

from __future__ import annotations

import json
import unittest

from tools.checks import CheckResult
from tools.scoring import (VERSION_METODO, compute_indice)


def _resultado(q: float, insufficient: bool = False) -> CheckResult:
    return CheckResult(
        valor_bruto={},
        normalizado=q,
        insufficient=insufficient,
        coverage=1.0,
    )


def _todos(qs: dict[str, float]) -> dict[str, CheckResult]:
    return {nombre: _resultado(q) for nombre, q in qs.items()}


CASOS_COMPLETOS = {
    "burstiness": 0.0,
    "mattr": 0.5,
    "uniformity": 1.0,
    "cliches_es": 0.25,
    "compression": 0.75,
}


class TestContribuciones(unittest.TestCase):
    def test_un_solo_check_disponible_es_100_q(self):
        informe = compute_indice({"mattr": _resultado(0.25)})
        self.assertAlmostEqual(informe["contribuciones"]["mattr"], 25.0, places=9)
        self.assertEqual(informe["indice_llm"], 25)

    def test_todos_disponibles_suma_y_contribuciones(self):
        informe = compute_indice(_todos(CASOS_COMPLETOS))
        # pesos ajustados tras topes de grupo: fuentes exactas del frozen table
        w_mattr = 100 * (0.17 * (0.32 / 0.35)) * 0.5
        w_burst = 100 * (0.18 * (0.32 / 0.35)) * 0.0
        w_unif = 100 * (0.18 * (0.40 / 0.42)) * 1.0
        w_clich = 100 * (0.24 * (0.40 / 0.42)) * 0.25
        w_comp = 100 * 0.23 * 0.75
        suma_pesos = 0.32 + 0.40 + 0.23
        esperado = {
            "mattr": w_mattr / suma_pesos,
            "burstiness": w_burst / suma_pesos,
            "uniformity": w_unif / suma_pesos,
            "cliches_es": w_clich / suma_pesos,
            "compression": w_comp / suma_pesos,
        }
        for nombre, valor in esperado.items():
            self.assertAlmostEqual(
                informe["contribuciones"][nombre], valor, places=6, msg=nombre
            )
        total = sum(informe["contribuciones"].values())
        self.assertAlmostEqual(total, informe["suma_contribuciones"], places=9)
        self.assertEqual(informe["indice_llm"], int(round(total)))
        self.assertEqual(informe["indice_llm"], 50)

    def test_peso_registrado_y_contribucion_llegan_al_resultado(self):
        informe = compute_indice({"compression": _resultado(1.0)})
        resultado = informe["resultado"]["compression"]
        self.assertAlmostEqual(resultado.contribucion, 100.0, places=9)
        self.assertAlmostEqual(resultado.peso, 0.23, places=9)

    def test_acotado_0_100(self):
        for qs in (
            {n: 1.0 for n in CASOS_COMPLETOS},
            {n: 0.0 for n in CASOS_COMPLETOS},
        ):
            informe = compute_indice(_todos(qs))
            self.assertGreaterEqual(informe["indice_llm"], 0)
            self.assertLessEqual(informe["indice_llm"], 100)


class TestTopesCorrelacion(unittest.TestCase):
    def test_grupo_mattr_burstiness_topeado(self):
        informe = compute_indice(
            _todos(CASOS_COMPLETOS)
        )
        # weirdo guard: caso base completo
        pesos = informe["pesos"]
        self.assertLessEqual(pesos["mattr"] + pesos["burstiness"], 0.32 + 1e-9)
        self.assertAlmostEqual(pesos["mattr"] / 0.17, pesos["burstiness"] / 0.18, places=9)

    def test_grupo_cliches_uniformity_topeado(self):
        informe = compute_indice(_todos(CASOS_COMPLETOS))
        pesos = informe["pesos"]
        self.assertLessEqual(pesos["cliches_es"] + pesos["uniformity"], 0.40 + 1e-9)
        self.assertAlmostEqual(
            pesos["cliches_es"] / 0.24, pesos["uniformity"] / 0.18, places=9
        )

    def test_compression_no_tocado_por_topes(self):
        informe = compute_indice(_todos(CASOS_COMPLETOS))
        self.assertAlmostEqual(informe["pesos"]["compression"], 0.23, places=9)


class TestRenormalizacionInsuficientes(unittest.TestCase):
    def test_solo_disponibles_en_el_denominador(self):
        resultados = {
            "mattr": _resultado(0.5),
            "compression": _resultado(0.5),
            "burstiness": _resultado(0.9, insufficient=True),
            "uniformity": _resultado(0.9, insufficient=True),
            "cliches_es": _resultado(0.9, insufficient=True),
        }
        informe = compute_indice(resultados)
        self.assertAlmostEqual(
            informe["contribuciones"]["mattr"], 100 * 0.17 * 0.5 / 0.40, places=9
        )
        self.assertAlmostEqual(
            informe["contribuciones"]["compression"], 100 * 0.23 * 0.5 / 0.40, places=9
        )
        self.assertEqual(informe["n_disponibles"], 2)

    def test_sin_disponibles_es_insufficient_text(self):
        resultados = {n: _resultado(0.9, insufficient=True) for n in CASOS_COMPLETOS}
        informe = compute_indice(resultados)
        self.assertTrue(informe["insufficient_text"])
        self.assertIsNone(informe["indice_llm"])
        self.assertEqual(informe["contribuciones"], {})

    def test_reporte_vacio_tambien_abstiene(self):
        informe = compute_indice({})
        self.assertTrue(informe["insufficient_text"])


class TestDeterminismoYOrden(unittest.TestCase):
    def test_determinista_y_json_ordenado(self):
        informe = compute_indice(_todos(CASOS_COMPLETOS))
        informe2 = compute_indice(_todos(CASOS_COMPLETOS))
        self.assertEqual(informe, informe2)
        dump = json.dumps(informe, sort_keys=True, ensure_ascii=False)
        dump2 = json.dumps(compute_indice(_todos(CASOS_COMPLETOS)), sort_keys=True,
                           ensure_ascii=False)
        self.assertEqual(dump, dump2)
        self.assertEqual(
            list(informe["contribuciones"]), sorted(informe["contribuciones"])
        )
        # F5.4: VERSION_METODO pasa a f4-integridad (la señal cambia con
        # semillas reales); actualización autorizada por el plan 5.4.
        self.assertEqual(VERSION_METODO, "f4-integridad")

    def test_q_fuera_de_rango_se_acota(self):
        # defensa: q>1 no debe romper la coherencia (se acota antes de pesar)
        informe = compute_indice({"mattr": _resultado(1.4)})
        self.assertLessEqual(informe["indice_llm"], 100)

    def test_check_desconocido_falla_claro(self):
        with self.assertRaises(ValueError):
            compute_indice({"desconocido": _resultado(0.5)})

    def test_version_metodo_f4_integridad(self):
        # F5.4: la versión del método y el JSON de compute_indice reportan
        # f4-integridad (los índices cambian de significado con semillas reales).
        informe = compute_indice(_todos(CASOS_COMPLETOS))
        self.assertEqual(VERSION_METODO, "f4-integridad")
        self.assertEqual(informe["version"], "f4-integridad")


if __name__ == "__main__":
    unittest.main()
