"""Diagnóstico híbrido: cruza el eje PROSA (indice_llm congelado) con el
eje ESTRUCTURA (tools/estructura) y clasifica con una tabla explícita.

Reglas fijas (mismas constantes documentadas en docs/diagnostico-hibrido.md):

- UMBRAL = 26 y MARGEN = 8 son constantes de ESTE módulo derivadas de la
  calibración F3 congelada; NO se recalculan y NO alteran ``indice_llm``
  ni el pipeline de scoring.
- Banda de abstención de prosa: ``UMBRAL - MARGEN`` <= prosa < ``UMBRAL``
  (18 <= prosa < 26): debajo del umbral hay señal débil, no concluyente.
- Estructura: ``valor`` >= 60 → «regular»; <= 40 → «irregular»; entre
  ambos → «intermedia»; ``insufficient`` → «insuficiente».

Tabla de categorías (EXPLÍCITA, sin casos ocultos):

    prosa >= 26 y estructura regular    → plantilla_prosa_y_estructura
    prosa >= 26 y estructura irregular  → probable_hibrido_estructura_propia_prosa_ia
    18 <= prosa < 26 (banda)            → prosa_no_concluyente (+ nota estructura)
    prosa <= 18 y estructura irregular  → sin_senal_suficiente
    prosa <= 18 y estructura regular    → estructura_regular_prosa_no_marcada
    prosa >= 26 con estructura intermedia/insuficiente,
    o prosa <= 18 con estructura intermedia/insuficiente →
    prosa_no_concluyente (honestidad: la combinación no está tabulada)

``no_concluyente`` es True en TODAS las categorías salvo
``plantilla_prosa_y_estructura`` (plantilla pura).

El módulo NO usa red ni aleatoriedad; NO introduce pesos nuevos; no
modifica el informe que recibe (puras lecturas).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "UMBRAL",
    "MARGEN",
    "banda_abstencion",
    "etiqueta_estructura",
    "diagnostico_hibrido",
]

# Umbral/margen congelados en F3 y heredados por el diagnóstico híbrido.
UMBRAL = 26
MARGEN = 8

FRONTERA_REGULAR = 60
FRONTERA_IRREGULAR = 40


def banda_abstencion() -> dict[str, int]:
    """Banda de abstención de prosa derivada del umbral/margen congelados."""
    return {
        "umbral": UMBRAL,
        "margen": MARGEN,
        "cota_inferior": UMBRAL - MARGEN,
        "cota_superior": UMBRAL,
    }


def etiqueta_estructura(eje: dict[str, Any]) -> str:
    """«regular» (>=60), «irregular» (<=40), «intermedia»/«insuficiente»."""
    if not isinstance(eje, dict) or "valor" not in eje:
        raise ValueError("eje_estructura invalido: falta 'valor'")
    if eje.get("insufficient"):
        return "insuficiente"
    valor = eje["valor"]
    if valor >= FRONTERA_REGULAR:
        return "regular"
    if valor <= FRONTERA_IRREGULAR:
        return "irregular"
    return "intermedia"


def diagnostico_hibrido(informe: dict[str, Any], eje: dict[str, Any]) -> dict[str, Any]:
    """Cruza prosa (indice_llm) y estructura en un dict JSON-nativo.

    ``informe`` debe exponer ``indice_llm`` (int); ``eje`` es la salida de
    ``tools.estructura.eje_estructura``. No muta ninguna de las dos
    entradas. Sin red, sin azar, sin pesos nuevos.
    """
    if not isinstance(informe, dict) or informe.get("indice_llm") is None:
        raise ValueError("informe invalido: se exige indice_llm numérico")
    prosa = informe["indice_llm"]
    if not isinstance(eje, dict) or "valor" not in eje:
        raise ValueError("eje_estructura invalido: falta 'valor'")
    etiqueta = etiqueta_estructura(eje)
    if prosa >= UMBRAL:
        if etiqueta == "regular":
            categoria = "plantilla_prosa_y_estructura"
            nota = (
                "Prosa con señal marcada de LLM y estructura regular tipo "
                "plantilla: patrón consistente con texto generado por IA. "
                "Es la única categoría concluyente del diagnóstico."
            )
            no_concluyente = False
        elif etiqueta == "irregular":
            categoria = "probable_hibrido_estructura_propia_prosa_ia"
            nota = (
                "La estructura no sigue una plantilla (irregular), pero la "
                "prosa sí muestra señal de LLM: posible borrador propio con "
                "párrafos generados por IA. Indicio, no prueba."
            )
            no_concluyente = True
        else:
            categoria = "prosa_no_concluyente"
            nota = (
                f"Prosa con señal marcada ({prosa} >= {UMBRAL}), pero la "
                f"estructura es {etiqueta}: la combinación no permite "
                "concluir plantilla pura ni híbrido."
            )
            no_concluyente = True
    elif prosa <= UMBRAL - MARGEN:
        if etiqueta == "irregular":
            categoria = "sin_senal_suficiente"
            nota = (
                "Ni la prosa ni la estructura muestran señal concluyente: "
                "no hay base objetiva para afirmar uso de IA ni para "
                "exculpar."
            )
            no_concluyente = True
        elif etiqueta == "regular":
            categoria = "estructura_regular_prosa_no_marcada"
            nota = (
                f"La prosa no muestra señal de LLM ({prosa} <= {UMBRAL - MARGEN}), "
                "pero la estructura sí es regular tipo plantilla: la "
                "regularidad estructural por sí sola no prueba nada."
            )
            no_concluyente = True
        else:
            categoria = "prosa_no_concluyente"
            nota = (
                f"Prosa sin señal ({prosa} <= {UMBRAL - MARGEN}) y estructura "
                f"{etiqueta}: no hay evidencia suficiente de IA."
            )
            no_concluyente = True
    else:
        categoria = "prosa_no_concluyente"
        extra = ""
        if etiqueta == "regular":
            extra = (
                " Ojo: 'estructura regular' no distingue una plantilla generada "
                "de un formato de trabajo propio (p. ej. escenas numeradas "
                "S01..S10 y secciones de tamaño parecido)."
            )
        nota = (
            f"El índice de prosa ({prosa}) cae en la banda de abstención "
            f"[{UMBRAL - MARGEN}, {UMBRAL}): decisión no concluyente. "
            f"Estructura: {etiqueta} (valor {eje['valor']}).{extra}"
        )
        no_concluyente = True
    return {
        "prosa": {
            "indice_llm": prosa,
            "banda_abstencion": banda_abstencion(),
        },
        "estructura": {
            "valor": eje["valor"],
            "etiqueta": etiqueta,
            "regularidad": eje.get("regularidad", 0.0),
            "n_secciones": eje.get("n_secciones", 0),
            "insufficient": bool(eje.get("insufficient")),
        },
        "categoria": categoria,
        "nota": nota,
        "no_concluyente": no_concluyente,
    }
