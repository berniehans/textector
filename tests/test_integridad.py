"""Regresiones de la auditoría: entradas reales, fronteras y aislamiento."""

import csv
import hashlib
import json
import tempfile
import unittest
import unicodedata
from pathlib import Path
from unittest.mock import patch

from tools import calibrate, cli
from tools.checks import cliches_es, compression, uniformity
from tools.decision import prediccion
from tools.diagnostico import diagnostico_hibrido
from tools.estructura import detectar_secciones, eje_estructura
from tools.lexicon import parse_yaml_min
from tools.textector_core import split_sentences, tokenize


class Entradas(unittest.TestCase):
    def test_unicode_equivalente_y_sin_invisibles(self):
        texto = "La canción de un niño en conclusión."
        self.assertEqual(tokenize(texto), tokenize(unicodedata.normalize("NFD", texto)))
        self.assertEqual(tokenize("ca\u200bsa"), ["casa"])
        self.assertEqual(cliches_es.check((texto + " ") * 15),
                         cliches_es.check((unicodedata.normalize("NFD", texto) + " ") * 15))

    def test_puntuacion_es_insuficiente(self):
        r = uniformity.check("!!!\n\n???\n\n...")
        self.assertTrue(r.insufficient)
        self.assertEqual(r.coverage, 0.0)

    def test_puntuacion_cli_error_limpio(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.stdin", io.StringIO("!!!\n\n???\n\n...")), redirect_stderr(err), redirect_stdout(out):
            self.assertEqual(cli.main(["analyze", "--stdin"]), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(len(err.getvalue().splitlines()), 1)
        self.assertNotIn("Traceback", err.getvalue())

    def test_config_semanticamente_invalida(self):
        for yaml in ("version: 1\n", "version: 1\ncliches: 5\n", "version: 1\nclichez: []\n",
                     "version: 1\ncliches: []\n", "version: 2\ncliches:\n  - \"casa|20|propio\"\n"):
            with self.subTest(yaml=yaml), self.assertRaises(ValueError):
                cliches_es.phrases_from_parsed(parse_yaml_min(yaml))

    def test_config_no_string_no_se_ignora(self):
        with self.assertRaises(ValueError):
            cliches_es.phrases_from_parsed({"version": 1, "cliches": ["casa|20|propio", 5]})

    def test_semillas_vacias_o_sin_tokens(self):
        texto = "Una muestra suficientemente larga. " * 20
        for semilla in ("", " \n", "!!!"):
            with self.subTest(semilla=semilla), self.assertRaises(ValueError):
                compression.check(texto, seed_ia=semilla, seed_hum="Una semilla válida")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "semilla.txt"
            path.write_text("!!!", encoding="utf-8")
            with self.assertRaises(cli.ErrorCLI):
                cli._cargar_semillas(path, path)

    def test_crlf_y_lf_puntuan_igual(self):
        texto = (calibrate.CORPUS / "llm/a01.txt").read_text(encoding="utf-8")
        self.assertEqual(calibrate.puntuar(texto), calibrate.puntuar(texto.replace("\n", "\r\n")))


class Segmentacion(unittest.TestCase):
    def test_cierres_multiples_no_pierden_prosa(self):
        texto = "«(Hola mundo.)» Otra frase."
        spans = split_sentences(texto)
        self.assertEqual([s.text for s in spans], ["«(Hola mundo.)»", "Otra frase."])
        for s in spans:
            self.assertEqual(texto[s.start:s.end], s.text)

    def test_elipsis_unicode_y_ascii_no_cortan(self):
        for signo in ("...", "…"):
            texto = f"Todo se detuvo{signo} Algo cambió."
            self.assertEqual([s.text for s in split_sentences(texto)], [texto])

    def test_formatos_cabecera_no_aportan_tokens(self):
        for cabecera in ("S01", "S01: Título", "## S01 — Título", "S01 - Título"):
            self.assertEqual([s.text for s in split_sentences(cabecera + "\nUn cuerpo.")], ["Un cuerpo."])


class Estructura(unittest.TestCase):
    def test_una_seccion_o_sin_contenido_abstiene(self):
        for texto in ("S01\nUna frase.", "S01\n\nS02", "S01\nUna frase.\nS02"):
            with self.subTest(texto=texto):
                self.assertTrue(eje_estructura(texto)["insufficient"])
                self.assertEqual(eje_estructura(texto)["valor"], 0)

    def test_bonus_usa_numero_y_no_titulo(self):
        sin = "S01\nUn cuerpo.\n\nS02\nUn cuerpo."
        con = "S01 — Uno\nUn cuerpo.\n\nS02 — Dos\nUn cuerpo."
        self.assertEqual(eje_estructura(sin)["valor"], eje_estructura(con)["valor"])
        falso = "S04 — S01\nUn cuerpo.\n\nS07 — S02\nUn cuerpo."
        self.assertLess(eje_estructura(falso)["valor"], eje_estructura(con)["valor"])

    def test_crlf_y_offsets_originales(self):
        texto = "S01 — Uno\r\nUn cuerpo.\r\n\r\nS02 — Dos\r\nUn cuerpo."
        self.assertEqual(eje_estructura(texto), eje_estructura(texto.replace("\r\n", "\n")))
        self.assertEqual(detectar_secciones(texto)[1][2], texto.index("S02"))


class Decision(unittest.TestCase):
    def test_todas_fronteras_comparten_regla(self):
        for indice in range(101):
            estado = prediccion(indice)
            for valor in (20, 50, 88):
                d = diagnostico_hibrido({"indice_llm": indice}, {"valor": valor})
                self.assertTrue(d["no_concluyente"])
                if estado == "abstencion":
                    self.assertEqual(d["categoria"], "prosa_no_concluyente")
                    self.assertIn("abstención", d["nota"])
                elif valor == 88:
                    esperada = "plantilla_prosa_y_estructura" if estado == "ia" else "estructura_regular_prosa_no_marcada"
                    self.assertEqual(d["categoria"], esperada)

    def test_no_acepta_nan_bool_ni_fuera_rango(self):
        for indice in (float("nan"), True, -1, 101, "31"):
            with self.assertRaises(ValueError):
                diagnostico_hibrido({"indice_llm": indice}, {"valor": 80})


class Corpus(unittest.TestCase):
    def test_hashes_reales_y_largos(self):
        import io
        for row in csv.DictReader(io.StringIO(calibrate.MANIFEST.read_text(encoding="utf-8"))):
            path = calibrate.CORPUS / calibrate._subcarpeta(row["id"]) / (row["id"] + ".txt")
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["SHA256"], row["id"])
            self.assertEqual(len(raw.decode("utf-8")), int(row["chars"]), row["id"])

    def test_semillas_documentadas_exactas(self):
        corpus = calibrate.cargar_corpus()
        semillas, fuentes = calibrate._semillas_para(corpus, calibrate.split_grupos(corpus)["train"])
        self.assertEqual(semillas, calibrate._semillas_reales())
        meta = json.loads(calibrate.SEED_MANIFEST.read_text(encoding="utf-8"))
        for clase, semilla in zip(("ia", "humana"), semillas):
            self.assertEqual(hashlib.sha256(semilla.encode()).hexdigest(), meta[clase]["sha256"])
            self.assertFalse(set(fuentes[clase]) & calibrate.HOLDOUT_V2)

    def test_carga_rechaza_corrupcion(self):
        with patch.object(Path, "read_bytes", return_value=b"contenido alterado"):
            with self.assertRaisesRegex(ValueError, "SHA256"):
                calibrate.cargar_corpus()


class Calibracion(unittest.TestCase):
    def test_tasas_indefinidas_y_cobertura(self):
        m = calibrate._matriz(["x"], {"x": 80}, {"x": "ia"}, 31, 2)
        met = calibrate._metricas(m)
        self.assertEqual(met["tpr"], 1.0)
        self.assertIsNone(met["tnr"])
        self.assertIsNone(met["balanced"])
        m = calibrate._matriz(["x"], {"x": 31}, {"x": "ia"}, 31, 2)
        self.assertIsNone(calibrate._metricas(m)["tpr"])
        self.assertEqual(calibrate._metricas(m)["cobertura_ia"], 0.0)

    def test_cv_perfecta_no_se_diluye_con_clases_ausentes(self):
        corpus = {p: {"texto": p + " texto único"} for p in ("a01", "a02", "h01", "h02")}
        llamadas = []
        def indice(texto, semillas=None):
            llamadas.append((texto[:3], semillas))
            return 90 if texto.startswith("a") else 10
        with patch.object(calibrate, "_indice_de", side_effect=indice):
            r = calibrate._barrido_train(corpus)
        self.assertEqual(r["cv"]["metricas"]["tpr"], 1.0)
        self.assertEqual(r["cv"]["metricas"]["tnr"], 1.0)
        self.assertEqual(r["cv"]["metricas"]["cobertura"], 1.0)
        self.assertEqual(len(r["cv"]["predicciones"]), 4)
        for fold in r["cv"]["folds"]:
            for ids in fold["fuentes_semillas"].values():
                self.assertFalse(set(ids) & set(fold["piezas"]))
            # Las semillas que realmente llegaron al scorer tampoco incluyen test.
            omitido = fold["piezas"][0]
            self.assertTrue(any(p == omitido and all(corpus[omitido]["texto"] not in s for s in semillas)
                                for p, semillas in llamadas))

    def test_holdout_no_puede_ser_fuente(self):
        with self.assertRaises(ValueError):
            calibrate._semillas_para({}, ["a05"])

    def test_holdout_exige_parametros_explicitos(self):
        with self.assertRaises(ValueError):
            calibrate.evaluar_holdout({})

    def test_main_no_abre_holdout_por_defecto(self):
        import io
        from contextlib import redirect_stdout
        with patch.object(calibrate, "cargar_corpus", return_value={}), patch.object(calibrate, "_barrido_train", return_value={}), patch.object(calibrate, "evaluar_holdout") as holdout, redirect_stdout(io.StringIO()):
            self.assertEqual(calibrate.main([]), 0)
        holdout.assert_not_called()


if __name__ == "__main__":
    unittest.main()
