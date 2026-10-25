"""Perfil F5 portable: índice fijo para prosa con o sin párrafos conservados.

El índice exige MATTR, densidad léxica y compresión. Ritmo y estructura se
reportan aparte; nunca cambian el denominador ni rellenan párrafos ausentes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.checks import burstiness, cliches_es, compression, mattr, uniformity
from tools.resources import recurso
from tools.textector_core import tokenize

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config/f5-portable.json"
PROFILE_RESOURCE = recurso("f5-portable.json", "config/f5-portable.json")
WEIGHTS = {"mattr": 0.45, "cliches_es": 0.25, "compression_positive_only": 0.30}
MARGIN = 4
MIN_TOKENS = 50
MIN_CLEAN_BYTES = 150
CLICHE_DENSITY_MAX = 25.0
CLICHE_EVIDENCE_HITS = 3
COMPRESSION_NEUTRAL_Q = 0.5


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _compression_positive(q: float) -> float:
    """Solo evidencia por encima del punto neutral contribuye al índice."""
    return _clamp((q - COMPRESSION_NEUTRAL_Q) / (1.0 - COMPRESSION_NEUTRAL_Q))


def _hash_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile() -> dict[str, Any]:
    profile = json.loads(PROFILE_RESOURCE.read_text(encoding="utf-8"))
    expected = {
        "version": "f5-portable-v1",
        "weights": WEIGHTS,
        "abstention_margin": MARGIN,
        "minimum_tokens": MIN_TOKENS,
        "minimum_clean_bytes": MIN_CLEAN_BYTES,
        "cliche_density_max_per_1000": CLICHE_DENSITY_MAX,
        "cliche_evidence_hits": CLICHE_EVIDENCE_HITS,
        "compression_neutral_q": COMPRESSION_NEUTRAL_Q,
        "paragraph_dependent_checks_in_index": False,
    }
    for key, value in expected.items():
        if profile.get(key) != value:
            raise ValueError(f"perfil F5 incoherente: {key}")
    if not 0 <= profile.get("threshold", -1) <= 100:
        raise ValueError("umbral F5 fuera de [0, 100]")
    return profile


def puntuar(text: str, lexicon: list[cliches_es.ClicheEntry],
            seeds: tuple[str, str]) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError("f5.puntuar espera str")
    profile = _profile()
    seed_ia, seed_hum = seeds
    tok_count = len(tokenize(text))
    q_mattr = mattr.check(text)
    r_cliche = cliches_es.check(text, lexicon=lexicon)
    r_compression = compression.check(text, seed_ia=seed_ia, seed_hum=seed_hum)
    auxiliary = {
        "burstiness": burstiness.check(text),
        "uniformity": uniformity.check(text),
    }

    missing: list[str] = []
    if tok_count < MIN_TOKENS or q_mattr.insufficient:
        missing.append("mattr")
    if tok_count < cliches_es.MIN_TOKENS or r_cliche.insufficient:
        missing.append("cliches_es")
    if r_compression.insufficient:
        missing.append("compression")

    clean_bytes = r_compression.valor_bruto.get("n_bytes_muestra", 0)
    if tok_count < MIN_TOKENS:
        missing_tokens = max(0, MIN_TOKENS - tok_count)
    else:
        missing_tokens = 0
    if clean_bytes < MIN_CLEAN_BYTES and "compression" not in missing:
        missing.append("compression")

    raw_q_lex = float(r_cliche.normalizado)
    hits = int(r_cliche.valor_bruto.get("n_hits_total", 0))
    density = float(r_cliche.valor_bruto.get("densidad_ponderada_por_1000", 0.0))
    q_lex = _clamp(density / CLICHE_DENSITY_MAX) * min(1.0, hits / CLICHE_EVIDENCE_HITS)
    q_comp = float(r_compression.normalizado)
    q_comp_positive = _compression_positive(q_comp)
    raw_qs = {"mattr": float(q_mattr.normalizado), "cliches_es": raw_q_lex,
              "compression": q_comp}
    effective_qs = {"mattr": raw_qs["mattr"], "cliches_es": q_lex,
                    "compression_positive_only": q_comp_positive}

    insufficient = sorted(set(missing))
    contributions = {name: WEIGHTS[name] * value * 100.0
                     for name, value in effective_qs.items()}
    score = None if insufficient else int(round(sum(contributions.values())))
    threshold = int(profile["threshold"])
    lower, upper = threshold - MARGIN, threshold + MARGIN
    decision = "abstencion" if score is None or lower <= score <= upper else (
        "ia" if score > upper else "humano")

    def result_data(result):
        return {"valor_bruto": result.valor_bruto, "normalizado": result.normalizado,
                "coverage": result.coverage, "insufficient": result.insufficient}

    return {
        "version": profile["version"], "indice_llm": score, "predicho": decision,
        "n_disponibles": 3 - len(insufficient),
        "umbral": threshold, "margen": MARGIN,
        "banda_abstencion": [lower, upper], "pesos_fijos": WEIGHTS,
        "denominador": 1.0, "n_tokens": tok_count, "n_bytes_limpios": clean_bytes,
        "checks_insuficientes": insufficient,
        "motivos_insuficiencia": {"tokens_faltantes": missing_tokens,
                                  "bytes_limpios_minimos": MIN_CLEAN_BYTES},
        "q_brutos": raw_qs, "q_efectivos": effective_qs,
        "contribuciones": contributions,
        "checks_portables": {"mattr": result_data(q_mattr),
                             "cliches_es": result_data(r_cliche),
                             "compression": result_data(r_compression)},
        "checks_auxiliares_fuera_del_indice": {
            name: result_data(result) for name, result in auxiliary.items()},
        "parrafos_usados_para_puntuar": False,
        "trazabilidad": {
            "perfil_sha256": _hash_file(PROFILE_RESOURCE),
            "lexicon_sha256": hashlib.sha256(json.dumps(
                [(e.frase_cruda, e.peso_raw, e.fuente) for e in lexicon],
                ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "sha256_seed_ia": hashlib.sha256(seed_ia.encode("utf-8")).hexdigest(),
            "sha256_seed_hum": hashlib.sha256(seed_hum.encode("utf-8")).hexdigest(),
        },
    }
