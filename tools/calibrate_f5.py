"""Calibra solo el umbral F5 en el corpus consumido external-v1.

Los pesos y el margen son parte fija del perfil. Este comando rechaza otros
corpus para mantener separado el conjunto reservado.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cli import _cargar_lexicon, _cargar_semillas
from tools.f5 import MARGIN, PROFILE_PATH, puntuar
from tools.resources import CONFIG


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pred(score: int | None, threshold: int) -> str:
    if score is None or threshold - MARGIN <= score <= threshold + MARGIN:
        return "abstencion"
    return "ia" if score > threshold + MARGIN else "humano"


def _summary(rows: list[dict[str, Any]], threshold: int) -> dict[str, Any]:
    out = Counter()
    for row in rows:
        label, pred = row["label"], _pred(row["score"], threshold)
        out["n"] += 1
        out["n_ia" if label == "ia" else "n_human"] += 1
        if pred == "abstencion":
            out["abstain_ia" if label == "ia" else "abstain_human"] += 1
        elif label == "ia":
            out["tp" if pred == "ia" else "fn"] += 1
        else:
            out["fp" if pred == "ia" else "tn"] += 1
    n_h, n_i = out["n_human"], out["n_ia"]
    coverage_h = (n_h - out["abstain_human"]) / n_h if n_h else None
    fp_rate = out["fp"] / n_h if n_h else None
    return {"threshold": threshold, "margin": MARGIN,
            "counts": {k: out[k] for k in ("n", "n_human", "n_ia", "tp", "tn", "fp", "fn", "abstain_human", "abstain_ia")},
            "human_decision_coverage": coverage_h, "fp_on_all_humans": fp_rate,
            "tp_on_all_ai": out["tp"] / n_i if n_i else None}


def calibrate(corpus: Path, write_profile: bool = False) -> dict[str, Any]:
    corpus = corpus.resolve()
    if corpus != (ROOT / "validation/external-v1").resolve():
        raise ValueError("F5 solo se calibra con validation/external-v1; reservado rechazado")
    if (ROOT / "validation/reserved-f5-v1/manifest.jsonl").exists() and corpus.name.startswith("reserved"):
        raise ValueError("el corpus reservado no se puede calibrar")
    manifest_raw = (corpus / "manifest.jsonl").read_bytes()
    rows = [json.loads(x) for x in manifest_raw.decode("utf-8").splitlines()]
    lexicon, seeds = _cargar_lexicon(CONFIG), _cargar_semillas()
    scored = []
    for row in rows:
        path = (corpus / row["path"]).resolve()
        if not path.is_relative_to(corpus) or sha(path.read_bytes()) != row["sha256"]:
            raise ValueError("integridad/ruta inválida en external-v1: " + row["id"])
        report = puntuar(path.read_text(encoding="utf-8"), lexicon, seeds)
        scored.append({"id": row["id"], "label": "ia" if row["label"] == "ia" else "human",
                       "panel": row["panel"], "group": row["group"],
                       "score": report["indice_llm"],
                       "checks_insuficientes": report["checks_insuficientes"]})
    candidates = [_summary(scored, t) for t in range(101)]
    acceptable = [x for x in candidates
                  if x["fp_on_all_humans"] <= 0.05
                  and x["human_decision_coverage"] >= 0.80]
    if not acceptable:
        chosen = None
        status = "sin_umbral_que_cumpla_las_cotas_en_desarrollo"
    else:
        best_tp = max(x["counts"]["tp"] for x in acceptable)
        # Fija el umbral más conservador entre los máximos de detección.
        chosen = min(x["threshold"] for x in acceptable if x["counts"]["tp"] == best_tp)
        status = "calibrado_en_desarrollo"
    result = {"id": "f5-development-calibration-v1", "status": status,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "dataset": "validation/external-v1", "dataset_role": "development_consumed",
              "manifest_sha256": sha(manifest_raw), "n": len(scored),
              "fixed_margin": MARGIN, "fixed_weights": {"mattr": .45, "cliches_es": .25,
                                                               "compression_positive_only": .30},
              "gates": {"fp_on_all_humans_max": .05,
                        "human_decision_coverage_min": .80},
              "selected_threshold": chosen,
              "selected_metrics": next((x for x in candidates if x["threshold"] == chosen), None),
              "candidates": candidates,
              "development_scores": scored,
              "reserved_set_read": False}
    if write_profile and chosen is not None:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        profile["threshold"] = chosen
        PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, sort_keys=True,
                                            indent=2) + "\n", encoding="utf-8", newline="\n")
        result["profile_sha256_after_calibration"] = sha(PROFILE_PATH.read_bytes())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "validation/external-v1")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-profile", action="store_true")
    args = parser.parse_args(argv)
    result = calibrate(args.corpus, args.write_profile)
    data = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(data, encoding="utf-8", newline="\n")
    else:
        print(data, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
