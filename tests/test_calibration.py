"""Tests F3 del aparato de calibración (ver docs/calibration.md).

Alcance honesto: NO abren el HOLDOUT en sentido operativo (no puntúan
textos del holdout ni dependen del umbral elegido). Solo verifican:

1. Aislamiento: ninguna ruta del HOLDOUT_V2 (h08, h16, h19, a05, a07,
   b03) contiene una subcadena de 50 chars de ninguna semilla
   (corpus/seeds/*.txt).
2. Corpus y manifest bien formados: cargar_corpus devuelve 40 textos
   (human + llm + news) y el manifest tiene exactamente 41 lineas
   (header + 40 datos), ids h01..h20 + a01..a10 + b01..b10, clase
   consistente con el prefijo (h=human; a y b=llm), campo SHA256 de 64
   hex y licencia no vacia en cada fila de datos; b03 debe caer en
   holdout (split por grupos).
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
_ID_RE = re.compile(r"^[hab]\d{2}$")
_ID_RE_HUM = re.compile(r"^h\d{2}$")
_ID_RE_IA = re.compile(r"^[ab]\d{2}$")


def _texto_holdout() -> dict[str, str]:
    """Lee (a planos, sin puntuar) los 6 textos del HOLDOUT_V2."""
    textos: dict[str, str] = {}
    for pid in sorted(calibrate.HOLDOUT_V2):
        sub = calibrate._subcarpeta(pid)
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
        self.assertGreaterEqual(len(rutas), 1)
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


class TestCorpusYManifestV2(unittest.TestCase):

    def test_corpus_carga_40_archivos(self):
        corpus = calibrate.cargar_corpus()
        self.assertEqual(len(corpus), 40)
        ids = set(corpus)
        self.assertEqual(
            ids,
            {f"h{i:02d}" for i in range(1, 21)}
            | {f"a{i:02d}" for i in range(1, 11)}
            | {f"b{i:02d}" for i in range(1, 11)},
        )
        for pid, fila in sorted(corpus.items()):
            with self.subTest(id=pid):
                self.assertTrue(fila["texto"].strip())
                esperado_dominio = calibrate._dominio_ia(pid)
                self.assertNotEqual(esperado_dominio, "")
                self.assertEqual(fila["dominio"], esperado_dominio)

    def test_split_grupos_v2(self):
        corpus = calibrate.cargar_corpus()
        s = calibrate.split_grupos(corpus)
        self.assertEqual(
            set(s["holdout"]), {"h08", "h16", "h19", "a05", "a07", "b03"})
        self.assertEqual(len(s["train"]), 34)
        grupos: dict[str, list[str]] = {}
        for pid in s["train"]:
            grupos.setdefault(calibrate._grupo_de(pid), []).append(pid)
        self.assertEqual(sorted(grupos["pereda"]), ["h14", "h17"])
        self.assertEqual(
            grupos["zenodo"],
            [f"b{i:02d}" for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)],
        )

    def test_manifest_bien_formado_v2(self):
        texto = calibrate.MANIFEST.read_text(encoding="utf-8")
        lineas = texto.splitlines()
        self.assertEqual(len(lineas), 41)  # header + 40 filas de datos
        reader = csv.DictReader(io.StringIO(texto))
        self.assertEqual(
            reader.fieldnames,
            ["id", "clase", "fuente", "obra_o_tema", "autor_o_modelo",
             "licencia", "chars", "SHA256"],
        )
        filas = list(reader)
        datos = [f for f in filas if _ID_RE.match((f["id"] or "").strip())]
        self.assertEqual(len(datos), 40)
        ids = {f["id"].strip() for f in datos}
        self.assertEqual(
            ids,
            {f"h{i:02d}" for i in range(1, 21)}
            | {f"a{i:02d}" for i in range(1, 11)}
            | {f"b{i:02d}" for i in range(1, 11)},
        )
        sha_re = re.compile(r"^[0-9a-f]{64}$")
        for f in datos:
            es_humano = bool(_ID_RE_HUM.match(f["id"].strip()))
            esperada = "human" if es_humano else "llm"
            sha_ok = bool(sha_re.fullmatch(f["SHA256"].strip()))
            with self.subTest(id=f["id"]):
                self.assertEqual(f["clase"].strip(), esperada)
                self.assertTrue(f["licencia"].strip())
                self.assertTrue(f["SHA256"].strip())
                self.assertTrue(sha_ok)
        notas = [f for f in filas if not _ID_RE.match((f["id"] or "").strip())]
        self.assertEqual(notas, [])  # v2: solo header + 40 filas de datos


class TestReproducibilidad(unittest.TestCase):

    def test_carga_del_corpus_reproducible(self):
        informe1 = calibrate.cargar_corpus()
        informe2 = calibrate.cargar_corpus()
        self.assertEqual(len(informe1), 40)
        data1 = json.dumps(informe1, sort_keys=True, ensure_ascii=False)
        data2 = json.dumps(informe2, sort_keys=True, ensure_ascii=False)
        self.assertEqual(
            hashlib.sha256(data1.encode("utf-8")).hexdigest(),
            hashlib.sha256(data2.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
