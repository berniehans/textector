"""Métricas puras del EJE ESTRUCTURA del diagnóstico híbrido.

Este módulo es un bloque APARTE del pipeline congelado F2: NO participa en
``indice_llm`` (no registra checks, no aporta pesos ni contribuciones) y no
toca ``tools/scoring`` ni ``tools/checks``. Mide solo la ARQUITECTURA del
documento: secciones numeradas ``S01``..., sus tamaños, párrafos y
proporción de diálogo, y la regularidad de ese esqueleto.

El eje estructura es INDEPENDIENTE del eje prosa (``indice_llm``): un texto
puede tener esqueleto rígido de plantilla con prosa IA, o prosa sin señal
con esqueleto regular. Por eso se reporta por separado.

Determinista, solo stdlib, sin red, sin I/O.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

__all__ = [
    "detectar_secciones",
    "metricas_estructura",
    "regularidad",
    "eje_estructura",
]

# Cabecera: hasta 3 '#', luego ``S\d+`` y O BIEN la linea es solo ``S01``
# O BIEN un separador [—,–,:,?] y el titulo.  ``S01`` a secas también cuenta.
_CABECERA_RE = re.compile(
    r"^#{0,3}[ \t]*S\d+(?:[ \t]*[—–:-][ \t]*(?P<titulo>.+?))?[ \t]*$"
)

# Párrafos: bloques separados por al menos una línea en blanco.
_PAR_SPLIT_RE = re.compile(r"\n[ \t]*\n")

# Rayas de dialogo españolas (misma convención que uniformity).
_RAYA = ("—", "–")

# Fronteras de las transformaciones monótonas de regularidad (documentadas
# en el docstring de ``regularidad``). Constantes del módulo, sin pesos
# nuevos: el bonus y los tramos CV no son pesos del índice congelado.
CV_LARGOS_LO = 0.05
CV_LARGOS_HI = 0.60
CV_PARAFRAFOS_LO = 0.15
CV_PARAFRAFOS_HI = 0.80
CV_DIALOGO_LO = 0.10
CV_DIALOGO_HI = 0.50
BONUS_CABECERAS = 0.05

REGLA_REFERENCIA = re.compile(r"S(\d+)")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _es_dialogo(parrafo: str) -> bool:
    return parrafo.lstrip().startswith(_RAYA)


def detectar_secciones(texto: str) -> list[tuple[int, str, int]]:
    """Detecta líneas de cabecera ``^#{0,3}\\s*S\\d+\\s*[—–:-][...]/``.

    La variante ``S01`` a secas (sin separador ni título) también cuenta.
    Devuelve ``[(i, titulo, start_char), ...]`` en orden de aparición:
    ``i`` es el ordinal de la sección (0-based), ``titulo`` es el texto
    tras el separador (o el token ``S01`` si no lo hay) y ``start_char``
    el offset del inicio de esa línea dentro de ``texto``.
    """
    if not isinstance(texto, str):
        raise TypeError("detectar_secciones espera str")
    secciones: list[tuple[int, str, int]] = []
    offset = 0
    for linea in texto.split("\n"):
        m = _CABECERA_RE.match(linea)
        if m:
            titulo = m.group("titulo") or linea.strip()
            secciones.append((len(secciones), titulo, offset))
        offset += len(linea) + 1  # +1 por el '\n' que split consume
    return secciones


def metricas_estructura(texto: str) -> dict[str, Any]:
    """Métricas por sección del documento (puras, sin I/O).

    Sin cabeceras de sección → ``{"insufficient": True, ...}`` (el eje no
    tiene base para puntuar). Con cabeceras, para CADA sección (el corte
    va desde su cabecera hasta la siguiente, o fin del texto):

    - ``largos_secciones``: chars del cuerpo DESPUÉS de la línea de
      cabecera (sin trailing whitespace); la cabecera misma no cuenta.
    - ``parrafos_por_seccion``: bloques separados por línea en blanco,
      excluyendo la cabecera.
    - ``ratio_dialogo`` por sección: fracción de párrafos que empiezan
      con raya («—»/«–»); 0.0 si la sección no tiene párrafos.

    Salida determinista con claves ordenadas al serializar.
    """
    if not isinstance(texto, str):
        raise TypeError("metricas_estructura espera str")
    secciones = detectar_secciones(texto)
    if not secciones:
        return {
            "insufficient": True,
            "n_secciones": 0,
            "largos_secciones": [],
            "parrafos_por_seccion": [],
            "ratio_dialogo": [],
            "titulos": [],
        }
    limites = [start for (_, _, start) in secciones] + [len(texto)]
    largos: list[int] = []
    n_parrafos: list[int] = []
    ratios: list[float] = []
    titulos: list[str] = []
    for (i, titulo, start), fin in zip(secciones, limites[1:]):
        bloque = texto[start:fin].rstrip()
        lineas = bloque.split("\n")
        cuerpo = "\n".join(lineas[1:]).rstrip()  # dejo la cabecera fuera
        largos.append(len(cuerpo))
        parrafos = [p.strip() for p in _PAR_SPLIT_RE.split(cuerpo) if p.strip()]
        n_parrafos.append(len(parrafos))
        if parrafos:
            ratio = sum(1 for p in parrafos if _es_dialogo(p)) / len(parrafos)
        else:
            ratio = 0.0
        ratios.append(round(ratio, 4))
        titulos.append(titulo)
    return {
        "insufficient": False,
        "n_secciones": len(secciones),
        "largos_secciones": largos,
        "parrafos_por_seccion": n_parrafos,
        "ratio_dialogo": ratios,
        "titulos": titulos,
    }


def _cv(valores: list[float]) -> float | None:
    """Coeficiente de variación (poblacional); None si no hay media > 0."""
    if not valores:
        return None
    media = statistics.fmean(valores)
    if media <= 0.0:
        return None
    return statistics.pstdev(valores) / media


def _tramo_cv(cv: float | None, lo: float, hi: float) -> float:
    """Transformación monótona decreciente CV→[0,1] con fronteras [lo, hi].

    cv <= lo → 1.0 (secciones clonadas); cv >= hi → 0.0 (esqueleto
    dispersado); lineal dentro del tramo. cv None (sin dato) → 0.5
    neutral: se cuenta como media del tramo para no inventar señal.
    """
    if cv is None:
        return 0.5
    return _clamp(1.0 - (cv - lo) / (hi - lo))


def regularidad(metricas: dict[str, Any]) -> float:
    """Regularidad del esqueleto en [0, 1] (0 = irregular, 1 = plantilla).

    Media de TRES transformaciones monótonas decrecientes con fronteras
    documentadas (ninguna es un peso del índice congelado; bloque aparte):

    1. CV de largos de sección en chars con tramo [CV_LARGOS_LO=0.05,
       CV_LARGOS_HI=0.60]: una plantilla clona secciones (CV bajo) y un
       documento orgánico las disparata (CV alto); 0.60 ya corresponde a
       razones de 4:1 y más entre secciones.
    2. CV de número de párrafos por sección con tramo [CV_PARAFRAFOS_LO=0.15,
       CV_PARAFRAFOS_HI=0.80]: más tolerante porque 1 párrafo extra en una
       sección larga ya mueve el CV; 0.80 ≈ secciones de 1 vs 10 párrafos.
    3. CV del ratio de diálogo ENTRE secciones con tramo
       [CV_DIALOGO_LO=0.10, CV_DIALOGO_HI=0.50]: en narrativa plantilla la
       mezcla de escenas de diálogo ES homogénea; en prosa orgánica las
       secciones alternan escenas y descripciones. Si ninguna sección
       tiene diálogo (media = 0) el componente es 0.5 neutral: no inventa
       señal ni por ausencia ni por homogeneidad.

    Bonus ``BONUS_CABECERAS`` (+0.05) si la numeración es consecutiva
    DESDE ``S01``: es la forma en que una plantilla numera sus secciones;
    numeración discontinua o que no empieza en 1 no aporta bonus. El
    total se acota a [0, 1] y se redondea a 4 decimales.

    ``insufficient`` → 0.0 (sin base para puntuar).
    """
    if not isinstance(metricas, dict):
        raise TypeError("regularidad espera dict de metricas_estructura")
    if metricas.get("insufficient"):
        return 0.0
    componentes = [
        _tramo_cv(_cv(metricas["largos_secciones"]), CV_LARGOS_LO, CV_LARGOS_HI),
        _tramo_cv(_cv(metricas["parrafos_por_seccion"]), CV_PARAFRAFOS_LO, CV_PARAFRAFOS_HI),
        _tramo_cv(_cv(metricas["ratio_dialogo"]), CV_DIALOGO_LO, CV_DIALOGO_HI),
    ]
    bonus = 0.0
    if metricas["n_secciones"] >= 2:
        numeros: list[int] = []
        for titulo in metricas["titulos"]:
            m = REGLA_REFERENCIA.search(titulo)
            if not m:
                numeros = []
                break
            numeros.append(int(m.group(1)))
        if numeros and numeros[0] == 1 and all(
            b - a == 1 for a, b in zip(numeros, numeros[1:])
        ):
            bonus = BONUS_CABECERAS
    return round(_clamp(statistics.fmean(componentes) + bonus), 4)


def eje_estructura(texto: str) -> dict[str, Any]:
    """Eje estructura completo del documento (dict JSON-nativo, determinista).

    - ``valor``: 0..100 = round(regularidad*100) (0 si ``insufficient``).
    - ``regularidad``: 0..1, ver ``regularidad``.
    - ``n_secciones``: número de secciones detectadas.
    - ``insufficient``: True si no hay cabeceras de sección.
    - ``hits``: líneas explicativas (una por sección + veredicto).
    """
    if not isinstance(texto, str):
        raise TypeError("eje_estructura espera str")
    metricas = metricas_estructura(texto)
    if metricas["insufficient"]:
        return {
            "valor": 0,
            "regularidad": 0.0,
            "n_secciones": 0,
            "insufficient": True,
            "hits": ["sin cabeceras 'S01...' detectadas: eje estructura sin base"],
        }
    reg = regularidad(metricas)
    hits: list[str] = []
    for i, (titulo, largos, n_par, ratio) in enumerate(
        zip(
            metricas["titulos"],
            metricas["largos_secciones"],
            metricas["parrafos_por_seccion"],
            metricas["ratio_dialogo"],
        )
    ):
        hits.append(
            f"S{i + 1:02d} '{titulo}': {largos} chars, {n_par} párrafos, diálogo {ratio:.2f}"
        )
    hits.append(f"regularidad del esqueleto = {reg:.4f} (0=irregular, 1=plantilla)")
    return {
        "valor": int(round(reg * 100)),
        "regularidad": reg,
        "n_secciones": metricas["n_secciones"],
        "insufficient": False,
        "hits": hits,
    }
