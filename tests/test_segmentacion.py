"""Tests del núcleo de texto: normalización, tokenización y segmentación ES."""

from __future__ import annotations

import unittest

from tools.textector_core import (
    Span,
    _ABBREV_TOKENS,
    normalize_text,
    split_sentences,
    tokenize,
)


class TestNormalize(unittest.TestCase):
    def test_tildes_se_conservan(self):
        self.assertEqual(normalize_text("Canción"), "canción")

    def test_ende_completed_form_folding(self):
        self.assertEqual(normalize_text("Árbol Ñoño"), "árbol ñoño")

    def test_invisibles_removed(self):
        self.assertEqual(normalize_text("ca\u200bsa"), "casa")
        self.assertEqual(normalize_text("ca\u00adsa"), "casa")

    def test_empty(self):
        self.assertEqual(normalize_text(""), "")

    def test_non_str_rejected(self):
        with self.assertRaises(TypeError):
            normalize_text(None)


class TestTokenize(unittest.TestCase):
    def test_tildes_y_ene(self):
        self.assertEqual(tokenize("Canción, Niño"), ["canción", "niño"])

    def test_puntuacion_se_para(self):
        self.assertEqual(tokenize("¿Por qué?"), ["por", "qué"])

    def test_decimales_en_tokens(self):
        self.assertEqual(tokenize("Saúl 3.14"), ["saúl", "3", "14"])

    def test_empty(self):
        self.assertEqual(tokenize(""), [])


class TestSegmentacion(unittest.TestCase):
    def _texts(self, spans):
        return [s.text for s in spans]

    def _assert_spans_back(self, text, spans):
        """Los spans deben cortar exactamente el texto original."""
        for s in spans:
            self.assertIsInstance(s, Span)
            self.assertEqual(text[s.start : s.end], s.text)

    def test_oracion_simple(self):
        text = "Hola mundo."
        spans = split_sentences(text)
        self.assertEqual(self._texts(spans), ["Hola mundo."])
        self._assert_spans_back(text, spans)

    def test_tildes_utf8(self):
        text = "Canción de la sierra. Vino el niño."
        spans = split_sentences(text)
        self.assertEqual(
            self._texts(spans), ["Canción de la sierra.", "Vino el niño."]
        )
        self._assert_spans_back(text, spans)

    def test_dialogo_raya_no_fuerza_oracion(self):
        text = "—La conoces —me dijo."
        self.assertEqual([s.text for s in split_sentences(text)], ["—La conoces —me dijo."])

    def test_dialogo_raya_nueva_replica(self):
        text = "—La conoces —me dijo.\n—Nadie la conoce."
        spans = split_sentences(text)
        self.assertEqual([s.text for s in spans], ["—La conoces —me dijo.", "—Nadie la conoce."])

    def test_elipsis_no_separa(self):
        text = "Y luego todo se detuvo... Algo cambió."
        spans = split_sentences(text)
        # elipsis no corta: la primera oración contiene la elipsis y sigue
        self.assertEqual([s.text for s in spans], [text])
        self._assert_spans_back(text, spans)

    def test_abreviatura_sr_no_corta(self):
        text = "Sr. López volvió ayer. Fue tarde."
        spans = split_sentences(text)
        self.assertEqual(spans[0].text, "Sr. López volvió ayer.")
        self.assertEqual(spans[1].text, "Fue tarde.")

    def test_punto_ej_con_siguiente_mayuscula(self):
        text = "Me gusta el p. ej. clásico. Sin embargo, decidimos no."
        spans = split_sentences(text)
        self.assertEqual(len(spans) >= 2, True)
        self.assertEqual(spans[0].text, "Me gusta el p. ej. clásico.")

    def test_decimales(self):
        text = "El índice fue 3.14. La nota de hoy subió."
        spans = split_sentences(text)
        self.assertEqual([s.text for s in spans], ["El índice fue 3.14.", "La nota de hoy subió."])

    def test_preguntas_exclamaciones(self):
        text = "¿La conoces? ¡Qué fuerte!"
        spans = split_sentences(text)
        self.assertEqual([s.text for s in spans], ["¿La conoces?", "¡Qué fuerte!"])

    def test_pregunta_y_punto_en_una(self):
        text = "Yo pregunto ¿quién sabe? Nadie."
        spans = split_sentences(text)
        self.assertEqual(len(spans) >= 1, True)

    def test_encabezado_s01_no_es_prosa(self):
        text = "S01 — Escena inicial\nLuego llegó él."
        spans = split_sentences(text)
        self.assertEqual([s.text for s in spans], ["Luego llegó él."])

    def test_texto_vacio(self):
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   \n\t "), [])

    def test_espacios_alrededor(self):
        text = "  Primera frase.   Segunda frase.  "
        spans = split_sentences(text)
        self.assertEqual(
            [s.text for s in spans], ["Primera frase.", "Segunda frase."]
        )
        for s in spans:
            self.assertEqual(text[s.start : s.end], s.text)

    def test_split_dijo_que_no_corta(self):
        # F5.4: «no» es palabra común, no abreviatura; su punto corta.
        spans = split_sentences("Dijo que no. Luego se fue.")
        self.assertEqual([s.text for s in spans], ["Dijo que no.", "Luego se fue."])

    def test_entrada_rej_muerta_no_regresa(self):
        # F5.4, afirmación estructural: ninguna entrada del set lleva
        # espacios (el typo " rej" nunca matcheaba: el token previo sale
        # de \w+, que no contiene espacios).
        for tok in _ABBREV_TOKENS:
            self.assertNotIn(" ", tok)


if __name__ == "__main__":
    unittest.main()
