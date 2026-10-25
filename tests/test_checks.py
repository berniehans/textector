"""Tests F2 de los checks léxicos/estructurales: burstiness, uniformity, mattr, cliches_es.

Reglas del slice F2 (ver .hermes/plans/2026-10-24_textector-f1-f4.md F2):
- Casos que AÍSLAN cada contribución (sin uso de azar: vocabulario determinista).
- Invarianza (aproximada donde corresponde) al duplicar el texto.
- Diálogos, tildes y repeticiones como casos de borde.
- Los umbrales son provisionales F2 y están CONGELADOS en esta fase; los
  asserts de frontera usan los mismos rangos documentados en docs/methodology.md.
"""

from __future__ import annotations

import unittest

from tools.checks import burstiness, cliches_es, mattr, uniformity
from tools.checks.cliches_es import decode_entries
from tools.checks.registry import get_check, list_checks
from tools.lexicon import parse_yaml_min
from tools.textector_core import tokenize

# Vocabularios deterministas (sin random): suficientes para ventanas de 50.
VOCAB = (
    "mesa viento piedra camino río sombra llave puerta arena fruta candil "
    "burbuja brote gaviota alfiler mediodía árbol cañón niebla huella "
    "brisa tacón barco firma lista laja chispa semilla laguna manzana "
    "espalda gorrión sardina muelle clover".split()
)
POCO_VARIADO = ("brisa", "niebla", "río", "arena", "sombra")

_LENS_HUMANO = [8, 22, 14, 35, 10, 28, 12, 30, 16, 24]


def _oracion(n_tokens: int, offset: int, vocab: tuple[str, ...] = VOCAB) -> str:
    """Oración determinista de ``n_tokens`` tokens (casefold-insensible)."""
    toks = [vocab[(offset + j) % len(vocab)] for j in range(n_tokens)]
    toks[0] = toks[0][0].upper() + toks[0][1:]  # mayúscula inicial -> separa oración
    return " ".join(toks) + "."


def _texto(lens: list[int], vocab: tuple[str, ...] = VOCAB) -> str:
    """Texto con oraciones de longitudes ``lens`` (mayúscula inicial por oración)."""
    parts: list[str] = []
    offset = 0
    for n in lens:
        parts.append(_oracion(n, offset, vocab))
        offset += n
    return " ".join(parts)


def _parrafo(n_tokens: int, offset: int, opener: str | None = None) -> str:
    """Párrafo de ``n_tokens`` tokens; ``opener`` fuerza apertura de 2 tokens."""
    toks = [VOCAB[(offset + j) % len(VOCAB)] for j in range(n_tokens)]
    if opener is not None:
        head = opener.split()
        toks = [head[0].capitalize()] + head[1:] + toks[2:]
    else:
        toks[0] = toks[0][0].upper() + toks[0][1:]
    return " ".join(toks) + "."


def _texto_parrafos(lens: list[int], opener: str | None = None) -> str:
    parts: list[str] = []
    offset = 0
    for n in lens:
        parts.append(_parrafo(n, offset, opener))
        offset += n
    return "\n\n".join(parts)


def _relleno(n_tokens: int, offset: int = 5000) -> str:
    """Relleno determinista (vocabulario grande, fuera del léxico de clichés)."""
    parts: list[str] = []
    offset_local = offset
    quedan = n_tokens
    while quedan > 0:
        n = min(12, quedan)
        parts.append(_oracion(n, offset_local))
        offset_local += n
        quedan -= n
    return " ".join(parts)


class TestBurstiness(unittest.TestCase):
    def test_uniforme_maximo_de_senial(self):
        res = burstiness.check(_texto([20] * 12))
        self.assertFalse(res.insufficient)
        self.assertAlmostEqual(res.normalizado, 1.0, places=9)
        self.assertEqual(res.valor_bruto["n_oraciones"], 12)

    def test_humano_con_variacion_deja_senial_baja(self):
        # cv_robusto = 8/19 ≈ 0.421 -> q = 1 - (0.421-0.20)/0.40 ≈ 0.447 (provisional)
        res = burstiness.check(_texto(_LENS_HUMANO))
        self.assertFalse(res.insufficient)
        self.assertLess(res.normalizado, 0.5)
        self.assertGreater(res.normalizado, 0.2)

    def test_invariante_aproximado_al_duplicar(self):
        t = _texto(_LENS_HUMANO)
        q1 = burstiness.check(t).normalizado
        q2 = burstiness.check(t + " " + t).normalizado
        self.assertAlmostEqual(q1, q2, places=9)  # mediana/MAD: exacta al duplicar

    def test_insuficiente_con_pocas_oraciones(self):
        res = burstiness.check(_texto([12, 18, 15, 20, 14, 22]))
        self.assertTrue(res.insufficient)
        self.assertEqual(res.normalizado, 0.0)
        self.assertLess(res.coverage, 1.0)
        self.assertIn("n_oraciones", res.valor_bruto)

    def test_dialogos_reportados_no_prohibidos(self):
        lens = [10, 12, 9, 14, 11, 13, 12, 10, 15, 11, 13, 14]
        texto = " ".join(_oracion(n, 700) for n in lens)
        con_dialogo = texto.replace(_oracion(10, 700), "—La conoces —me dijo.")
        res = burstiness.check(con_dialogo)
        self.assertFalse(res.insufficient)
        self.assertGreaterEqual(res.valor_bruto["n_dialogo"], 1)


class TestUniformity(unittest.TestCase):
    def test_parrafos_uniformes_y_aperturas_repetidas_suben(self):
        res = uniformity.check(_texto_parrafos([20] * 6, opener="las sombras del"))
        self.assertFalse(res.insufficient)
        # cv parrafo = 0 -> q_disp = 1; share apertura = 1.0 -> q_rep = 1
        self.assertAlmostEqual(res.normalizado, 1.0, places=9)

    def test_variados_bajan_la_senial(self):
        res = uniformity.check(_texto_parrafos([8, 26, 10, 34, 14, 30]))
        self.assertFalse(res.insufficient)
        self.assertLess(res.normalizado, 0.2)

    def test_indicadores_separados_en_bruto(self):
        res = uniformity.check(_texto_parrafos([12, 18, 15, 14, 16, 20], opener="en el"))
        self.assertIn("q_dispersion", res.valor_bruto)
        self.assertIn("q_repeticion", res.valor_bruto)
        self.assertAlmostEqual(
            res.normalizado,
            (res.valor_bruto["q_dispersion"] + res.valor_bruto["q_repeticion"]) / 2,
            places=9,
        )

    def test_invariante_aproximado_al_duplicar(self):
        t = _texto_parrafos([10, 16, 12, 14, 18, 15])
        q1 = uniformity.check(t).normalizado
        q2 = uniformity.check(t + "\n\n" + t).normalizado
        self.assertAlmostEqual(q1, q2, places=9)

    def test_insuficiente_casi_pocos_parrafos(self):
        res = uniformity.check(_texto_parrafos([14, 16]))
        self.assertTrue(res.insufficient)
        self.assertEqual(res.normalizado, 0.0)
        self.assertLess(res.coverage, 1.0)

    def test_solo_dialogos_no_producen_repeticion_falsa(self):
        lineas = ["—La conoces —me dijo.", "—No sabía nada.", "—Escoba y fuera."]
        dialogos = "\n\n".join(lineas * 2)
        res = uniformity.check(dialogos)
        self.assertFalse(res.insufficient)
        self.assertEqual(res.valor_bruto["n_dialogo"], 6)
        self.assertTrue(res.valor_bruto["sin_prosa"])


class TestMattr(unittest.TestCase):
    def test_vocabulario_pobre_da_senial_maxima(self):
        toks = [POCO_VARIADO[i % len(POCO_VARIADO)] for i in range(300)]
        text = " ".join(toks)
        res = mattr.check(text)
        self.assertFalse(res.insufficient)
        self.assertAlmostEqual(res.normalizado, 1.0, places=9)

    def test_vocabulario_rico_no_senala(self):
        # 60 tokens todos distintos -> toda ventana de 50 tiene TTR = 1.0
        toks = [f"palabra{i}" for i in range(60)]
        res = mattr.check(" ".join(toks))
        self.assertFalse(res.insufficient)
        self.assertAlmostEqual(res.normalizado, 0.0, places=9)

    def test_insuficiente_sin_ttr_silencioso(self):
        res = mattr.check(" ".join(VOCAB[:20]))
        self.assertTrue(res.insufficient)
        self.assertEqual(res.normalizado, 0.0)
        self.assertNotIn("mattr", res.valor_bruto)  # sin TTR "silencioso"
        self.assertIn("n_tokens", res.valor_bruto)

    def test_invariante_aproximado_al_duplicar(self):
        toks = [VOCAB[i % len(VOCAB)] for i in range(260)]
        t = " ".join(toks)
        q1 = mattr.check(t).normalizado
        q2 = mattr.check(t + " " + t).normalizado
        self.assertAlmostEqual(q1, q2, delta=0.03)  # ventanas de unión: aproximado


class TestClichesEs(unittest.TestCase):
    def _lexicon(self, extra: list[str] | None = None) -> list[cliches_es.ClicheEntry]:
        base = ["en el fondo|60|x-fuente", "una __ que parecía|40|x-fuente"]
        return decode_entries(base + (extra or []))

    def test_hit_unico_anonimizado(self):
        base = _relleno(200)  # relleno controlado para pasar el mínimo 
        text = base + " En el fondo, nadie lo esperaba."
        res = cliches_es.check(text, lexicon=self._lexicon())
        self.assertFalse(res.insufficient)
        self.assertEqual(len(res.hits), 1)
        self.assertEqual(res.hits[0]["id"], 0)
        self.assertIn("pos", res.hits[0])
        # sin texto crudo del hit en la salida (positions/conteos anonimizados)
        dump = repr(res.valor_bruto) + repr(res.hits)
        self.assertNotIn("en el fondo", dump.lower())

    def test_comillas_y_tildes_casefold(self):
        lex = decode_entries(["podía haber jurado que|50|x-fuente"])
        text = _relleno(200) + " PODÍA HABER JURADO QUE llovía."
        res = cliches_es.check(text, lexicon=lex)
        self.assertEqual(len(res.hits), 1)

    def test_wildcard_un_token(self):
        lex = self._lexicon()
        bien = _relleno(200) + " una ciudad que parecía dormida."
        res_bien = cliches_es.check(bien, lexicon=lex)
        ids = [h["id"] for h in res_bien.hits]
        self.assertIn(1, ids)
        sin = _relleno(200) + " una que parecía dormida."
        res_sin = cliches_es.check(sin, lexicon=self._lexicon())
        self.assertNotIn(1, [h["id"] for h in res_sin.hits])

    def test_densidad_sube_con_peso_del_cliche(self):
        leve = decode_entries(["en el fondo|20|x-fuente"])
        grave = decode_entries(["en el fondo|80|x-fuente"])
        text = _relleno(2000).replace(".", ".\n") + " En el fondo, había algo."
        # garantiza el hit aunque el relleno no lo interfiera
        text = text + _relleno(500) + " En el fondo"
        q_leve = cliches_es.check(text, lexicon=leve).normalizado
        q_grave = cliches_es.check(text, lexicon=grave).normalizado
        self.assertGreater(q_grave, q_leve)

    def test_invariante_exacto_al_duplicar(self):
        text = _relleno(400) + " En el fondo. una flota que parecía."
        q1 = cliches_es.check(text, lexicon=self._lexicon()).normalizado
        q2 = cliches_es.check(text + " " + text, lexicon=self._lexicon()).normalizado
        # conteos y tokens se dupliquen -> densidad idéntica
        self.assertAlmostEqual(q1, q2, places=9)

    def test_insuficiente_con_pocos_tokens(self):
        res = cliches_es.check(" ".join(VOCAB[:30]), lexicon=self._lexicon())
        self.assertTrue(res.insufficient)
        self.assertEqual(res.normalizado, 0.0)
        self.assertEqual(res.hits, [])

    def test_sin_cliches_no_hay_senial(self):
        lex = decode_entries(["frase inexistente|80|x-fuente"])
        res = cliches_es.check(_relleno(200), lexicon=lex)
        self.assertFalse(res.insufficient)
        self.assertAlmostEqual(res.normalizado, 0.0, places=9)

    def test_decode_entries_rechaza_malformato(self):
        with self.assertRaises(ValueError):
            decode_entries(["solo dos|40"])
        with self.assertRaises(ValueError):
            decode_entries(["frase|abc|fuente"])
        with self.assertRaises(ValueError):
            decode_entries(["frase|120|fuente"])
        with self.assertRaises(ValueError):
            decode_entries(["frase|-3|fuente"])
        with self.assertRaises(ValueError):
            decode_entries(["|40|fuente"])

    def test_yaml_real_integra_con_lexicon(self):
        from pathlib import Path

        cfg = Path(__file__).resolve().parent.parent / "config" / "cliches_es.yaml"
        parsed = parse_yaml_min(cfg.read_text(encoding="utf-8"))
        lex = cliches_es.phrases_from_parsed(parsed)
        self.assertGreaterEqual(len(lex), 15)
        self.assertTrue(all(0.0 <= e.peso_units <= 10.0 for e in lex))


class TestRegistro(unittest.TestCase):
    def test_los_cinco_checks_registrados(self):
        import tools.checks.compression  # noqa: F401

        nombres = {e.name for e in list_checks()}
        esperados = {"burstiness", "uniformity", "mattr", "cliches_es", "compression"}
        self.assertTrue(esperados.issubset(nombres))
        for nombre in sorted(esperados):
            entry = get_check(nombre)
            self.assertGreater(entry.peso, 0.0)


if __name__ == "__main__":
    unittest.main()
