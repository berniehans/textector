"""Tests del eje ESTRUCTURA (tools/estructura, bloque aparte del scoring)."""

from __future__ import annotations

import copy
import json
import unittest

from tools.estructura import (
    eje_estructura,
    metricas_estructura,
    regularidad,
    detectar_secciones,
)

# Párrafo neutro (~150 chars) que NO casa con la regla de cabeceras.
_PARRAFO = (
    "Los medidores remotos registran el caudal del río en cada estación de "
    "monitoreo, y los técnicos revisan los valores al final de cada semana."
)


def _secciones_irregulares() -> str:
    """3 secciones S01..S03 muy dispares en largo y párrafos."""
    bloques: list[str] = []
    esquema = [
        ("S01 — Apertura", 1, 1),
        ("S02 — Desarrollo", 5, 5),
        ("S03 — Cierre y anexos", 9, 9),
    ]
    for titulo, n_par, n_palabras in esquema:
        texto_par = _PARRAFO[: n_palabras * 24] if n_palabras < 5 else _PARRAFO
        bloques.append(titulo)
        bloques.append("\n\n".join([texto_par] * n_par))
    return "\n\n".join(bloques) + "\n"


def _plantilla() -> str:
    """6 secciones S01..S06 con largos y párrafos casi idénticos."""
    bloques = []
    for i in range(1, 7):
        bloques.append(f"S0{i} — Sección {i}")
        bloques.append("\n\n".join([_PARRAFO] * 5))
    return "\n\n".join(bloques) + "\n"


class DetectarSecciones(unittest.TestCase):
    def test_formatos_de_cabecera(self) -> None:
        texto = "## S01 — Introducción\nprosa.\n\nS02: Método\nprosa.\n\nS03"
        secciones = detectar_secciones(texto)
        self.assertEqual(
            [(i, t) for i, t, _ in secciones],
            [(0, "Introducción"), (1, "Método"), (2, "S03")],
        )

    def test_offsets_de_linea(self) -> None:
        texto = "S01 — A\ncuerpo\n\nS02 — B\ncuerpo"
        secciones = detectar_secciones(texto)
        self.assertEqual(len(secciones), 2)
        offsets = [s for _, _, s in secciones]
        self.assertEqual(offsets[0], 0)
        self.assertEqual(texto[offsets[1]:].startswith("S02"), True)

    def test_no_cabeza_en_medio_de_linea(self) -> None:
        texto = "Citamos la norma S01 — no es cabecera.\n"
        self.assertEqual(detectar_secciones(texto), [])

    def test_determinista(self) -> None:
        texto = _plantilla()
        self.assertEqual(detectar_secciones(texto), detectar_secciones(texto))


class MetricasEstructura(unittest.TestCase):
    def test_sin_cabeceras_insufficient(self) -> None:
        m = metricas_estructura("Texto sin ninguna cabecera de sección.\n")
        self.assertTrue(m["insufficient"])
        self.assertEqual(m["n_secciones"], 0)

    def test_metricas_por_seccion(self) -> None:
        texto = (
            "S01 — A\n\n" + _PARRAFO + "\n\n— «¿Vendrás mañana?»\n\n"
            "S02 — B\n\n" + _PARRAFO + "\n\n" + _PARRAFO + "\n"
        )
        m = metricas_estructura(texto)
        self.assertFalse(m["insufficient"])
        self.assertEqual(m["n_secciones"], 2)
        self.assertEqual(m["parrafos_por_seccion"], [2, 2])
        self.assertEqual(m["ratio_dialogo"], [0.5, 0.0])
        self.assertEqual(m["titulos"], ["A", "B"])
        # la cabecera no cuenta en el largo del cuerpo
        for largo, titulo in zip(m["largos_secciones"], m["titulos"]):
            self.assertLess(largo, len(texto))

    def test_determinista(self) -> None:
        self.assertEqual(
            metricas_estructura(_secciones_irregulares()),
            metricas_estructura(_secciones_irregulares()),
        )


class Regularidad(unittest.TestCase):
    def test_irregular_baja(self) -> None:
        m = metricas_estructura(_secciones_irregulares())
        reg = regularidad(m)
        self.assertLess(reg, 0.5, f"esperaba regularidad baja, obtuve {reg}")

    def test_plantilla_alta(self) -> None:
        m = metricas_estructura(_plantilla())
        reg = regularidad(m)
        self.assertGreater(reg, 0.7, f"esperaba regularidad alta, obtuve {reg}")

    def test_insufficient_es_cero(self) -> None:
        self.assertEqual(
            regularidad(metricas_estructura("Sin cabeceras.")), 0.0
        )

    def test_monotonia_en_cv_de_largos(self) -> None:
        base = metricas_estructura(_plantilla())
        # duplicar una sección empeora el CV de largos → regularidad baja/baja-igual
        perturbado = copy.deepcopy(base)
        perturbado["largos_secciones"][0] = max(perturbado["largos_secciones"]) * 10
        self.assertLessEqual(
            regularidad(perturbado),
            regularidad(base),
            "regularidad debe caer (o no subir) al disparatar largos",
        )


class EjeEstructura(unittest.TestCase):
    def test_dict_completo_plantilla(self) -> None:
        eje = eje_estructura(_plantilla())
        self.assertFalse(eje["insufficient"])
        self.assertEqual(eje["n_secciones"], 6)
        self.assertGreater(eje["valor"], 70)
        self.assertTrue(eje["hits"])
        json.dumps(eje, sort_keys=True)  # JSON-nativo

    def test_sin_secciones(self) -> None:
        eje = eje_estructura("prosa libre sin secciones.\n")
        self.assertTrue(eje["insufficient"])
        self.assertEqual(eje["valor"], 0)
        self.assertEqual(eje["n_secciones"], 0)

    def test_determinista(self) -> None:
        self.assertEqual(eje_estructura(_plantilla()), eje_estructura(_plantilla()))

    def test_acepta_str_solo(self) -> None:
        with self.assertRaises(TypeError):
            eje_estructura(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
