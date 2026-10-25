"""Tests F3 del aparato de calibración (ver docs/calibration.md).

Alcance honesto: NO abren el HOLDOUT en sentido operativo (no puntúan
textos del holdout ni dependen del umbral elegido). Solo verifican:

1. Aislamiento: ninguna ruta del HOLDOUT (h03, h04, h08, a05, a09)
   contiene una subcadena de 50 chars de ninguna semilla
   (corpus/seeds/seed_ia_es.txt, seed_hum_es.txt).
2. Manifest bien formado: exactamente 22 lineas (20 datos + 1 nota + 1
   header), ids h01..h10 + a01..a10, clase consistente con el prefijo y
   licencia no vacia en cada fila de datos.
3. Reproducibilidad: cargar el corpus 2 veces produce el mismo SHA256
   del informe en memoria (serializacion canonica del dict cargado).

Determinista, stdlib, sin red y sin puntuar (no llama puntuar ni
evaluar_holdout).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unittest

from tools import calibrate

# Semilla de aislamiento: subcadena de la semilla que NO debe aparecer
# en ningun texto del holdout.
_VENTANA = 50
# Paso < ventana garantiza que cualquier coincidencia de >= 50 chars
# contenga el inicio de alguna ventana (sin huecos de detección).
_PASO = 5
_ID_RE = re.compile(r"^[ha]\d{2}$")


def _texto_holdout() -> dict[str, str]:
    """Lee (a planos, sin puntuar) los 5 textos del HOLDOUT."""
    textos: dict[str, str] = {}
    for pid in sorted(calibrate.HOLDOUT):
        sub = "human" if pid.startswith("h") else "llm"
        textos[pid] = (
            calibrate.CORPUS / sub / (pid + ".txt")
        ).read_text(encoding="utf-8")
    return textos


def _ventanas(texto: str) -> list[str]:
    """Ventanas deslizantes deterministas de _VENTANA chars con paso _PASO."""
    if len(texto) < _VENTANA:
        return []
    return [
        texto[i:i + _VENTANA]
        for i in range(0, len(texto) - _VENTANA + 1, _PASO)
    ]


class TestAislamientoHoldout(unittest.TestCase):

    def test_holdout_no_contiene_subcadenas_de_semillas(self):
        rutas = sorted((calibrate.CORPUS / "seeds").glob("*.txt"))
        self.assertGreaterEqual(len(rutas), 2)
        textos = _texto_holdout()
        contaminadas: list[tuple[str, str, str]] = []
        for ruta in rutas:
            semilla = ruta.read_text(encoding="utf-8")
            for chunk in _ventanas(semilla):
                for pid, contenido in textos.items():
                    if chunk in contenido:
                        contaminadas.append((ruta.name, pid, chunk))
        if contaminadas:
            detalle = "; ".join(
                f"{s}/{p} contains {r!r}" for s, p, r in contaminadas[:5]
            )
            self.fail(
                f"{len(contaminadas)} solapamiento(s) semilla-holdout: {detalle}"
            )


class TestManifest(unittest.TestCase):

    def test_manifest_bien_formado(self):
        texto = calibrate.MANIFEST.read_text(encoding="utf-8")
        lineas = texto.splitlines()
        self.assertEqual(len(lineas), 22)
        reader = csv.DictReader(io.StringIO(texto))
        self.assertEqual(
            reader.fieldnames,
            ["id", "clase", "fuente", "obra_o_tema", "autor_o_modelo",
             "licencia", "chars", "SHA256"],
        )
        filas = list(reader)
        datos = [f for f in filas if _ID_RE.match((f["id"] or "").strip())]
        self.assertEqual(len(datos), 20)
        ids = {f["id"].strip() for f in datos}
        self.assertEqual(
            ids,
            {f"h{i:02d}" for i in range(1, 11)}
            | {f"a{i:02d}" for i in range(1, 11)},
        )
        for f in datos:
            esperada = "human" if f["id"].startswith("h") else "llm"
            with self.subTest(id=f["id"]):
                self.assertEqual(f["clase"].strip(), esperada)
                self.assertTrue(f["licencia"].strip())
        notas = [f for f in filas if not _ID_RE.match((f["id"] or "").strip())]
        self.assertEqual(len(notas), 1)
        nota_texto = " ".join(n for n in notas[0].values() if n)
        self.assertIn("corte manual", nota_texto)


class TestReproducibilidad(unittest.TestCase):

    def test_carga_del_corpus_reproducible(self):
        informe1 = calibrate.cargar_corpus()
        informe2 = calibrate.cargar_corpus()
        self.assertEqual(len(informe1), 20)
        data1 = json.dumps(informe1, sort_keys=True, ensure_ascii=False)
        data2 = json.dumps(informe2, sort_keys=True, ensure_ascii=False)
        self.assertEqual(
            hashlib.sha256(data1.encode("utf-8")).hexdigest(),
            hashlib.sha256(data2.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
