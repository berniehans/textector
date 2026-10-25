"""Lectura descriptiva de prosa y estructura; ninguna categoría prueba autoría."""

from typing import Any

from tools.decision import UMBRAL, MARGEN, banda_abstencion, prediccion

FRONTERA_REGULAR = 60
FRONTERA_IRREGULAR = 40


def etiqueta_estructura(eje: dict[str, Any]) -> str:
    if not isinstance(eje, dict) or "valor" not in eje:
        raise ValueError("eje_estructura invalido: falta 'valor'")
    if eje.get("insufficient"):
        return "insuficiente"
    valor = eje["valor"]
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 100:
        raise ValueError("valor estructural fuera de [0, 100]")
    if valor >= FRONTERA_REGULAR:
        return "regular"
    if valor <= FRONTERA_IRREGULAR:
        return "irregular"
    return "intermedia"


def diagnostico_hibrido(informe: dict[str, Any], eje: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(informe, dict):
        raise ValueError("informe invalido")
    prosa = informe.get("indice_llm")
    if isinstance(prosa, bool) or not isinstance(prosa, int) or not 0 <= prosa <= 100:
        raise ValueError("informe invalido: se exige indice_llm entero en [0, 100]")
    etiqueta = etiqueta_estructura(eje)
    estado = prediccion(prosa)
    categoria = "prosa_no_concluyente"
    if estado == "ia" and etiqueta == "regular":
        categoria = "plantilla_prosa_y_estructura"
    elif estado == "ia" and etiqueta == "irregular":
        categoria = "probable_hibrido_estructura_propia_prosa_ia"
    elif estado == "humano" and etiqueta == "irregular":
        categoria = "sin_senal_suficiente"
    elif estado == "humano" and etiqueta == "regular":
        categoria = "estructura_regular_prosa_no_marcada"
    if estado == "abstencion":
        nota = (f"Índice {prosa} en la banda de abstención inclusiva "
                f"[{UMBRAL - MARGEN}, {UMBRAL + MARGEN}]. ")
    elif estado == "ia":
        nota = "Prosa con señales de estilo por encima de la referencia provisional. "
    else:
        nota = "Prosa sin señal suficiente según la referencia provisional. "
    nota += (f"Estructura {etiqueta}. La regularidad puede responder a un formato propio. "
             "Diagnóstico descriptivo no concluyente: no prueba autoría ni exculpa. "
             "El método f4 requiere validación con corpus y holdout nuevos.")
    return {
        "prosa": {"indice_llm": prosa, "banda_abstencion": banda_abstencion()},
        "estructura": {"valor": eje["valor"], "etiqueta": etiqueta,
                       "regularidad": eje.get("regularidad", 0.0),
                       "n_secciones": eje.get("n_secciones", 0),
                       "insufficient": bool(eje.get("insufficient"))},
        "categoria": categoria, "nota": nota, "no_concluyente": True,
    }
