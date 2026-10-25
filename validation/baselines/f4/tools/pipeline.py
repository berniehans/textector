"""Pipeline compartido por CLI y calibración; cinco checks, una sola política."""

import hashlib
import json
from typing import Any

from tools.checks import burstiness, cliches_es, compression, mattr, uniformity
from tools.scoring import compute_indice

MINIMO_CHECKS = 5


def puntuar(
    texto: str,
    lexicon: list[cliches_es.ClicheEntry],
    semillas: tuple[str, str],
) -> dict[str, Any]:
    seed_ia, seed_hum = semillas
    informe = compute_indice({
        "burstiness": burstiness.check(texto),
        "mattr": mattr.check(texto),
        "uniformity": uniformity.check(texto),
        "cliches_es": cliches_es.check(texto, lexicon=lexicon),
        "compression": compression.check(texto, seed_ia=seed_ia, seed_hum=seed_hum),
    })
    if informe["n_disponibles"] != MINIMO_CHECKS:
        informe["indice_llm"] = None
        informe["insufficient_text"] = True
    datos = [(e.frase_cruda, e.peso_raw, e.fuente) for e in lexicon]
    informe["lexicon_sha256"] = hashlib.sha256(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return informe
