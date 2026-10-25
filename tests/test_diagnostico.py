"""Tests del diagnóstico híbrido (tabla de categorías + pureza)."""

from __future__ import annotations

import copy
import json
import unittest

from tools.diagnostico import (
    banda_abstencion,
    diagnostico_hibrido,
    etiqueta_estructura,
)

INFORME = {"indice_llm": 40, "version": "f2", "n_disponibles": 5}


def _eje(valor: int, insufficient: bool = False, n_pct: int = 6) -> dict:
    return {
        "valor": valor,
        "regularidad": round(valor / 100, 4),
        "n_secciones": n_pct,
        "insufficient": insufficient,
        "hits": [],
    }


def _caso(indice: int, valor: int, insufficient: bool = False) -> dict:
    return diagnostico_hibrido(
        {"indice_llm": indice, "version": "f2"}, _eje(valor, insufficient)
    )


class TablaCategorias(unittest.TestCase):
    def test_plantilla_pura(self) -> None:
        d = _caso(40, 75)
        self.assertEqual(d["categoria"], "plantilla_prosa_y_estructura")
        self.assertFalse(d["no_concluyente"])

    def test_hibrido_estructura_propia(self) -> None:
        d = _caso(40, 20)
        self.assertEqual(
            d["categoria"], "probable_hibrido_estructura_propia_prosa_ia"
        )
        self.assertTrue(d["no_concluyente"])

    def test_banda_abstencion_prosa(self) -> None:
        d = _caso(22, 75)
        self.assertEqual(d["categoria"], "prosa_no_concluyente")
        self.assertTrue(d["no_concluyente"])
        self.assertIn("abstención", d["nota"])

    def test_sin_senal_suficiente(self) -> None:
        d = _caso(10, 20)
        self.assertEqual(d["categoria"], "sin_senal_suficiente")
        self.assertTrue(d["no_concluyente"])

    def test_estructura_regular_prosa_no_marcada(self) -> None:
        d = _caso(10, 75)
        self.assertEqual(
            d["categoria"], "estructura_regular_prosa_no_marcada"
        )
        self.assertTrue(d["no_concluyente"])

    def test_fronteras_exactas(self) -> None:
        # prosa == 26 va al ramal marcado; prosa == 18 al ramal sin señal.
        self.assertEqual(_caso(26, 75)["categoria"], "plantilla_prosa_y_estructura")
        self.assertEqual(
            _caso(18, 20)["categoria"], "sin_senal_suficiente"
        )

    def test_combinaciones_no_tabuladas_son_concluyentes(self) -> None:
        # estructura intermedia o insuficiente → nunca concluye
        d = _caso(40, 50)
        self.assertEqual(d["categoria"], "prosa_no_concluyente")
        self.assertTrue(d["no_concluyente"])
        d2 = diagnostico_hibrido(
            {"indice_llm": 10, "version": "f2"},
            _eje(0, insufficient=True, n_pct=0),
        )
        self.assertEqual(d2["categoria"], "prosa_no_concluyente")
        self.assertEqual(
            d2["estructura"]["etiqueta"], "insuficiente"
        )

    def test_no_concluyente_salvo_plantilla(self) -> None:
        casos = [(40, 75), (40, 20), (22, 75), (10, 20), (10, 75)]
        for indice, valor in casos:
            with self.subTest(indice=indice, valor=valor):
                d = _caso(indice, valor)
                esperado = d["categoria"] == "plantilla_prosa_y_estructura"
                self.assertEqual(d["no_concluyente"], not esperado)


class ContratoInjectivo(unittest.TestCase):
    def test_no_modifica_el_informe_ni_el_eje(self) -> None:
        informe = copy.deepcopy(INFORME)
        eje = _eje(75)
        eje_copia = copy.deepcopy(eje)
        d = diagnostico_hibrido(informe, eje)
        self.assertEqual(informe, INFORME)
        self.assertEqual(eje, eje_copia)
        self.assertEqual(d["prosa"]["indice_llm"], 40)

    def test_salida_json_nativa_y_determinista(self) -> None:
        json.dumps(_caso(22, 75), sort_keys=True, ensure_ascii=False)
        self.assertEqual(_caso(22, 75), _caso(22, 75))

    def test_banda_y_etiquetas(self) -> None:
        self.assertEqual(
            banda_abstencion(),
            {"umbral": 26, "margen": 8, "cota_inferior": 18, "cota_superior": 26},
        )
        self.assertEqual(etiqueta_estructura(_eje(60)), "regular")
        self.assertEqual(etiqueta_estructura(_eje(59)), "intermedia")
        self.assertEqual(etiqueta_estructura(_eje(40)), "irregular")
        self.assertEqual(etiqueta_estructura(_eje(0, True)), "insuficiente")

    def test_entrada_invalida(self) -> None:
        with self.assertRaises(ValueError):
            diagnostico_hibrido({"version": "f2"}, _eje(75))
        with self.assertRaises(ValueError):
            diagnostico_hibrido(INFORME, {"sin": "valor"})


if __name__ == "__main__":
    unittest.main()
