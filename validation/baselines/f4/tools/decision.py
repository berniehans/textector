"""Regla única de abstención. Referencia histórica, todavía provisional en f4."""

UMBRAL = 31
MARGEN = 2
ESTADO = "provisional-sin-validacion-f4"


def prediccion(indice: int | None, umbral: int = UMBRAL, margen: int = MARGEN) -> str:
    if indice is None or abs(indice - umbral) <= margen:
        return "abstencion"
    return "ia" if indice > umbral else "humano"


def banda_abstencion() -> dict[str, int | str]:
    return {"umbral": UMBRAL, "margen": MARGEN,
            "cota_inferior": UMBRAL - MARGEN,
            "cota_superior": UMBRAL + MARGEN, "estado": ESTADO}
