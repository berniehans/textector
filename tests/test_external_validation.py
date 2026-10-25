"""Contratos de la evaluación externa; no vuelven a puntuar el benchmark."""

import json
from pathlib import Path
import unittest

from tools.fetch_external_corpus import _canonical, _prefix_records
from tools.validate_external import resumir


class TestMetricasExternas(unittest.TestCase):
    def test_abstenciones_no_cuentan_como_aciertos(self):
        casos = [
            {"label": "human", "predicho": "ia", "indice_llm": 50, "checks_insuficientes": []},
            {"label": "human", "predicho": "humano", "indice_llm": 20, "checks_insuficientes": []},
            {"label": "human", "predicho": "abstencion", "indice_llm": None, "checks_insuficientes": ["uniformity"]},
            {"label": "ia", "predicho": "ia", "indice_llm": 50, "checks_insuficientes": []},
            {"label": "ia", "predicho": "abstencion", "indice_llm": 31, "checks_insuficientes": []},
        ]
        r = resumir(casos)
        self.assertEqual(r["conteos"]["fp"], 1)
        self.assertEqual(r["conteos"]["tn"], 1)
        self.assertEqual(r["conteos"]["tp"], 1)
        self.assertEqual(r["metricas"]["cobertura_decision"], 3 / 5)
        self.assertEqual(r["metricas"]["especificidad_condicionada"], .5)
        self.assertEqual(r["metricas"]["detecciones_ia_sobre_total_ia"], .5)
        self.assertEqual(r["conteos"]["abstencion_banda"], 1)
        self.assertEqual(r["conteos"]["abstencion_insuficiencia"], 1)

    def test_cobertura_cero_no_es_sensibilidad_cero(self):
        r = resumir([{"label": "ia", "predicho": "abstencion", "indice_llm": None,
                      "checks_insuficientes": ["uniformity"]}])
        self.assertEqual(r["metricas"]["cobertura_decision"], 0)
        self.assertIsNone(r["metricas"]["sensibilidad_condicionada"])
        self.assertEqual(r["conteos"]["fn"], 0)

    def test_muestra_vacia_no_inventa_tasas(self):
        r = resumir([])
        self.assertIsNone(r["metricas"]["sensibilidad_condicionada"])
        self.assertIsNone(r["metricas"]["especificidad_condicionada"])


class TestRestauracion(unittest.TestCase):
    def test_crcrlf_no_inventa_parrafos(self):
        self.assertEqual(_canonical("Una línea\r\r\notra línea\r\r\n\r\r\nPárrafo"),
                         "Una línea\notra línea\n\nPárrafo")

    def test_prefijo_incompleto_lee_solo_registros_completos(self):
        raw = '[{"story":"uno"}, {"story":"dos"}, {"story":'.encode()
        self.assertEqual(_prefix_records(raw, count=2), [{"story": "uno"}, {"story": "dos"}])

    def test_fechas_manifest_y_protocolo(self):
        root = Path(__file__).resolve().parents[1] / "validation/external-v1"
        rows = [json.loads(line) for line in (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 590)
        self.assertEqual(len({r["id"] for r in rows}), 590)
        humanos = [r for r in rows if r["label"] == "human"]
        self.assertEqual(len(humanos), 90)
        self.assertTrue(all(r["source_date"] < "2020-01-01" for r in humanos))
        self.assertEqual(len({r["group"] for r in humanos}), 9)
        self.assertTrue(all(r["old_overlap_20_tokens"] is False for r in rows))
