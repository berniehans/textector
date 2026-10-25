"""Secondary robustness check: test each AI checkpoint after excluding it from fit.

This is a reviewer-requested sensitivity after the primary structure screen.
It uses the already extracted, development-only features; it does not open any
new corpus or change the frozen feature family, classifier, or F5 configuration.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np

from tools.f5_experiments.structure_screen import (
    EXP, OUT, PROFILES, fit_logistic, fold_assignment, matrix,
    operating_cutoff, predict, read_jsonl, row_weights, sha,
)

OOF = OUT / "oof-predictions.jsonl"
LABELS = EXP / "language-audit-labels.jsonl"
DEST = OUT / "source-holdout-sensitivity.json"
N_INNER = 5
MODELS = ("M1_B0_length", "M2_B0_length_structure")


def run() -> dict:
    if DEST.exists():
        raise FileExistsError(f"refusing to overwrite {DEST}")
    labels = {r["id"]: r for r in read_jsonl(LABELS)}
    raw = read_jsonl(OOF)
    rows = []
    for r in raw:
        label = r["label"]
        if label == "ai":
            aud = labels.get(r["id"])
            if not aud or aud.get("language") != "espanol":
                continue
            weight = float(aud["sampling_weight"])
        else:
            weight = 1.0
        rows.append({"id": r["id"], "label": label, "checkpoint": r["source"],
                     "prompt_id": r["prompt_id"], "human_group": r["author_group"],
                     "sampling_weight": weight, "features": r["features"]})
    human_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r["label"] == "human":
            human_counts[r["human_group"]] += 1
    for r in rows:
        if r["label"] == "human":
            r["sampling_weight"] = 1.0 / human_counts[r["human_group"]]

    sources = sorted({r["checkpoint"] for r in rows if r["label"] == "ai"})
    results = {model: {} for model in MODELS}
    for source in sources:
        all_train = [r for r in rows if r["label"] == "human" or
                     (r["label"] == "ai" and r["checkpoint"] != source)]
        held_ai = [r for r in rows if r["label"] == "ai" and r["checkpoint"] == source]
        fold_h = fold_assignment([r for r in all_train if r["label"] == "human"], "human_group", N_INNER)
        fold_a = fold_assignment([r for r in all_train if r["label"] == "ai"], "prompt_id", N_INNER)
        folds = {**fold_h, **fold_a}
        for model_name in MODELS:
            calibration: dict[str, float] = {}
            for fold in range(N_INNER):
                train = [r for r in all_train if folds[str(r["id"])] != fold]
                valid = [r for r in all_train if folds[str(r["id"])] == fold]
                xtr, _ = matrix(train, model_name)
                xv, _ = matrix(valid, model_name)
                y = np.asarray([r["label"] == "ai" for r in train], dtype=int)
                fitted = fit_logistic(xtr, y, row_weights(train))
                for r, p in zip(valid, predict(fitted, xv)):
                    calibration[str(r["id"])] = float(p)
            ordered = sorted(all_train, key=lambda r: str(r["id"]))
            cut = operating_cutoff(ordered, np.asarray([calibration[str(r["id"])] for r in ordered]))
            xtr, _ = matrix(all_train, model_name)
            xhold, _ = matrix(held_ai, model_name)
            y = np.asarray([r["label"] == "ai" for r in all_train], dtype=int)
            final_model = fit_logistic(xtr, y, row_weights(all_train))
            p_hold = predict(final_model, xhold)
            w = np.asarray([r["sampling_weight"] for r in held_ai], dtype=float)
            detection = float(w[p_hold >= cut].sum() / w.sum())
            calibration_h = [r for r in ordered if r["label"] == "human"]
            h_pred = np.asarray([calibration[str(r["id"])] >= cut for r in calibration_h])
            h_w = np.asarray([r["sampling_weight"] for r in calibration_h], dtype=float)
            fp_oof = float(h_w[h_pred].sum() / h_w.sum())
            results[model_name][source] = {
                "heldout_ai_n": len(held_ai), "heldout_prompts": len({r["prompt_id"] for r in held_ai}),
                "heldout_detection_weighted": detection,
                "training_sources": len(sources) - 1, "training_ai_n": sum(r["label"] == "ai" for r in all_train),
                "training_human_authors": len({r["human_group"] for r in all_train if r["label"] == "human"}),
                "threshold_from_inner_group_oof": float(cut),
                "training_human_fp_inner_oof": fp_oof,
            }
    deltas = {src: results["M2_B0_length_structure"][src]["heldout_detection_weighted"] -
              results["M1_B0_length"][src]["heldout_detection_weighted"] for src in sources}
    result = {
        "status": "secondary_source_holdout_sensitivity_not_confirmatory",
        "deviation_note": "Added after primary screen at Astra review; features, classifier, and all thresholds frozen by primary protocol.",
        "uses_reserved_data": False, "f5_threshold_margin_changed": False,
        "source_count": len(sources), "models": results, "delta_M2_minus_M1_by_heldout_source": deltas,
        "macro_detection_M1": float(np.mean([results["M1_B0_length"][s]["heldout_detection_weighted"] for s in sources])),
        "macro_detection_M2": float(np.mean([results["M2_B0_length_structure"][s]["heldout_detection_weighted"] for s in sources])),
        "macro_delta": float(np.mean(list(deltas.values()))),
        "sources_with_at_least_5pp_gain": sum(v >= .05 for v in deltas.values()),
        "limitations": ["Only eight held-out checkpoints, each with 12–18 prompts.",
                        "Human false-positive calibration is inner-OOF within development, not independent confirmation.",
                        "Macro source average is descriptive; no aggregate promotion claim."],
        "sha256": {"primary_oof_predictions": sha(OOF.read_bytes()), "language_labels": sha(LABELS.read_bytes()),
                   "runner": sha(Path(__file__).read_bytes())},
    }
    DEST.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps({"status": r["status"], "macro_M1": r["macro_detection_M1"],
                      "macro_M2": r["macro_detection_M2"], "delta": r["macro_delta"],
                      "sources_gain_5pp": r["sources_with_at_least_5pp_gain"],
                      "output": str(DEST)}, ensure_ascii=False, indent=2))
