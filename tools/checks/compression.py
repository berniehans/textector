"""Check compression: señal por compresión sembrada (método zippy redefinido).

Port del MECANISMO de thinkst/zippy (auditoría en docs/audit_zippy.md), NO
de su código ni de su semilla EN:

- Deflate REAL: ``zlib.compressobj(level=6, wbits=-15)`` (raw DEFLATE,
  stdlib, determinista).
- Semillas: las fixtures sintéticas F2 viven en el propio módulo
  (``semilla_ia`` / ``semilla_humana``, mecánica). Desde F5 el check
  acepta semillas ES reales inyectadas como str (``seed_ia=``/
  ``seed_hum=``: ambas o ninguna); quien orquesta (CLI/calibrate) las
  carga de ``corpus/seeds/``. Validar el MECANISMO, no el desempeño.
- Limpieza ES conservadora (diferencia deliberada frente a zippy, que
  destruye tildes y ñ): el texto se reduce a tokens casefold unidos por
  espacio — conserva a-z con diacríticos; pierde puntuación, que es ruido
  para la comparación de estilo.
- Marginales por bytes del texto: m_seed = (c(seed+" "+sample) − c(seed))
  / bytes(sample). Delta = m_ia − m_h.
- q = clamp(0.5 − delta / ESCALA_DELTA) con ESCALA_DELTA congelada en 0.40.

Cobertura insuficiente (muestra limpia < ``MIN_BYTES_MUESTRA``) →
``insufficient``. ``insufficient`` NO es veredicto. Determinista, sin I/O,
sin red, sin azar.
"""

from __future__ import annotations

import hashlib
import zlib

from tools.checks import CheckResult
from tools.checks.registry import register_check
from tools.scoring import PESOS
from tools.textector_core import normalize_text, tokenize

__all__ = [
    "check",
    "semilla_ia",
    "semilla_humana",
    "MIN_BYTES_MUESTRA",
    "ESCALA_DELTA",
    "MAX_TOKENS",
]

MIN_BYTES_MUESTRA = 150
ESCALA_DELTA = 0.40
MAX_TOKENS = 30000
_LEVEL = 6
_WBITS = -15

# -----------------------------------------------------------------------------
# Semillas sintéticas deterministas (fixtures de mecánica; las ES reales
# entran inyectadas desde F5)
# -----------------------------------------------------------------------------

_CONECTORES = ("Además", "Por otra parte", "Sin embargo", "A su vez")
_TEMAS = ("la memoria", "el viento", "la ciudad", "las estaciones",
          "la costumbre", "la sombra")
_VERBOS = ("avanza", "cambia", "reclama", "sostiene")
_SUST = ("lado", "borde", "centro", "relieve", "sombras")
_ADJ = ("antiguo", "frío", "plano", "claro")

_PAL_HUMANO = (
    "árbol cañón río penumbra llave chispa rincón barro cariño mediodía "
    "escoba sirena puntero brisa azotea sardina garbanzo termo ardilla "
    "camino borugo guayaba tiple lagaña canoa albañil grifo malla nuca "
    "trapiche cumbia cierre pólvora salero".split()
)
_RESPUESTAS = ("—No sé.", "—Ahora no, Lena.", "—Está bien.")


def _semilla_ia_texto() -> str:
    """Fixture estilo 'LLM-narración': longitudes uniformes + conectores.
    Determinista: sustitución modular sobre tuplas fijas (sin azar)."""
    oraciones: list[str] = []
    for i in range(96):
        conector = _CONECTORES[i % 4]
        tema = _TEMAS[i % 6]
        verbo = _VERBOS[i % 4]
        s1 = _SUST[i % 5]
        s2 = _SUST[(i + 2) % 5]
        adj = _ADJ[i % 4]
        oraciones.append(
            f"{conector}, {tema} {verbo} hacia el {s1} del barrio y el {s2} "
            f"se queda como eco {adj} del tiempo."
        )
    parrafos = [" ".join(oraciones[i : i + 3]) for i in range(0, len(oraciones), 3)]
    return "\n\n".join(parrafos)


def _semilla_humana_texto() -> str:
    """Fixture estilo 'humano': longitudes variadas, ráfagas, réplicas.
    Determinista: sustitución modular sobre tuplas fijas (sin azar)."""
    oraciones: list[str] = []
    for i in range(96):
        n = (i % 7) + 3  # 3..9 tokens: longitud desigual
        toks = [_PAL_HUMANO[(i * 5 + j) % len(_PAL_HUMANO)] for j in range(n)]
        frase1 = " ".join(toks)
        if i % 4 == 1:
            frase1 = frase1[0].upper() + frase1[1:] + ", sin remedio."
        elif i % 4 == 3:
            frase1 = _RESPUESTAS[i % 3]
        else:
            frase1 = frase1[0].upper() + frase1[1:] + "."
        oraciones.append(frase1)
    parrafos: list[str] = []
    actual: list[str] = []
    for i, oracion in enumerate(oraciones):
        actual.append(oracion)
        if (i % 5) == 4 or (i % 3) == 0:
            parrafos.append(" ".join(actual))
            actual = []
    if actual:
        parrafos.append(" ".join(actual))
    return "\n\n".join(parrafos)


_SEMILLA_IA: str | None = None
_SEMILLA_HUMANA: str | None = None


def semilla_ia() -> str:
    """Semilla IA sintética (fixture F2); constante en el proceso."""
    global _SEMILLA_IA
    if _SEMILLA_IA is None:
        _SEMILLA_IA = _semilla_ia_texto()
    return _SEMILLA_IA


def semilla_humana() -> str:
    """Semilla humana sintética (fixture F2); constante en el proceso."""
    global _SEMILLA_HUMANA
    if _SEMILLA_HUMANA is None:
        _SEMILLA_HUMANA = _semilla_humana_texto()
    return _SEMILLA_HUMANA


# -----------------------------------------------------------------------------
# Mecánica de compresión
# -----------------------------------------------------------------------------

def _raw_deflate(data: bytes) -> int:
    compressor = zlib.compressobj(level=_LEVEL, wbits=_WBITS)
    chunk = compressor.compress(data)
    return len(chunk + compressor.flush())


def _limpiar(texto: str) -> str:
    """Reduce el texto a tokens casefold unidos; conserva tildes/ñ (diferencia
    deliberada frente a ``clean_text`` de zippy, quien las borra)."""
    return " ".join(tokenize(normalize_text(texto)))


def _marginal(seed_clean: str, sample_clean: str) -> float:
    """m = (c(seed + sample) − c(seed)) / bytes(sample): bytes agregados por
    byte de muestra (perplexidad proxy: menor → texto más predecible)."""
    sep = " " if seed_clean and sample_clean else ""
    base = seed_clean.encode("utf-8")
    completo = (seed_clean + sep + sample_clean).encode("utf-8")
    n_bytes = len(sample_clean) and len(sample_clean.encode("utf-8"))
    if n_bytes == 0:
        return 0.0
    return float(_raw_deflate(completo) - _raw_deflate(base)) / float(n_bytes)


def check(
    text: str,
    seed_ia: str | None = None,
    seed_hum: str | None = None,
) -> CheckResult:
    """Señal de compresión sembrada en [0, 1] (puro, determinista).

    Sin inyección usa las fixtures sintéticas F2 (retrocompatibilidad de
    mecánica). Con semillas reales inyectadas (AMBAS, como str crudos) las
    limpia una vez por llamada y reporta trazabilidad: etiqueta
    ``reales-es`` y sha256 de cada semilla cruda. La inyección mixta (una
    sola semilla) se rechaza: mezclar real con sintética bajo una etiqueta
    única contaminaría el reporte. Sin I/O: las semillas entran como str.
    """
    if not isinstance(text, str):
        raise TypeError("compression.check espera str")
    if seed_ia is None and seed_hum is None:
        etiqueta = "sinteticas-f2"
        trazabilidad: dict[str, str] = {}
        seed_ia_cruda = semilla_ia()
        seed_h_cruda = semilla_humana()
    else:
        if seed_ia is None or seed_hum is None:
            raise ValueError(
                "inyección mixta: seed_ia y seed_hum deben inyectarse juntas o ausentes"
            )
        if not isinstance(seed_ia, str) or not isinstance(seed_hum, str):
            raise TypeError("las semillas inyectadas deben ser str")
        etiqueta = "reales-es"
        trazabilidad = {
            "sha256_seed_ia": hashlib.sha256(seed_ia.encode("utf-8")).hexdigest(),
            "sha256_seed_hum": hashlib.sha256(seed_hum.encode("utf-8")).hexdigest(),
        }
        seed_ia_cruda = seed_ia
        seed_h_cruda = seed_hum
    if not _limpiar(seed_ia_cruda) or not _limpiar(seed_h_cruda):
        raise ValueError("las semillas deben contener tokens léxicos")
    sample = " ".join(tokenize(normalize_text(text)))
    n_bytes = len(sample.encode("utf-8"))
    coverage = min(1.0, n_bytes / MIN_BYTES_MUESTRA)
    if n_bytes < MIN_BYTES_MUESTRA:
        return CheckResult(
            valor_bruto={"n_bytes_muestra": n_bytes},
            normalizado=0.0,
            insufficient=True,
            coverage=coverage,
        )
    truncado = False
    toks = sample.split(" ")
    if len(toks) > MAX_TOKENS:
        sample = " ".join(toks[:MAX_TOKENS])
        truncado = True
        n_bytes = len(sample.encode("utf-8"))
    seed_ia_limpia = _limpiar(seed_ia_cruda)
    seed_h_limpia = _limpiar(seed_h_cruda)
    m_ia = _marginal(seed_ia_limpia, sample)
    m_h = _marginal(seed_h_limpia, sample)
    delta = m_ia - m_h
    q = max(0.0, min(1.0, 0.5 - delta / ESCALA_DELTA))
    return CheckResult(
        valor_bruto={
            "n_bytes_muestra": n_bytes,
            "n_seed_ia": len(seed_ia_limpia.encode("utf-8")),
            "n_seed_h": len(seed_h_limpia.encode("utf-8")),
            "m_ia": round(m_ia, 4),
            "m_h": round(m_h, 4),
            "delta": round(delta, 4),
            "escala": ESCALA_DELTA,
            "semillas": etiqueta,
            "nivel": "mecanica" if not truncado else "muestra-truncada",
            **trazabilidad,
        },
        normalizado=q,
        coverage=1.0,
        hits=[f"delta={delta:.3f}"],
    )


register_check("compression", check, categoria="señal", peso=PESOS["compression"])
