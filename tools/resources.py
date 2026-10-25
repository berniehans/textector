"""Recursos del checkout o del wheel, sin depender del directorio de trabajo."""

from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def recurso(nombre: str, ruta_checkout: str):
    # Un checkout incompleto debe fallar cerrado; no ocultarlo con otro recurso.
    if (ROOT / "pyproject.toml").is_file():
        return ROOT / ruta_checkout
    return files("tools").joinpath("data", nombre)


CONFIG = recurso("cliches_es.yaml", "config/cliches_es.yaml")
SEED_IA = recurso("seed_ia_es.txt", "corpus/seeds/seed_ia_es.txt")
SEED_HUM = recurso("seed_hum_es.txt", "corpus/seeds/seed_hum_es.txt")
