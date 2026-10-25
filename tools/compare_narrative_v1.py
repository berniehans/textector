"""Evalúa una vez la reserva narrativa; compara F4 congelado y F5 portable."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cli import _cargar_lexicon, _cargar_semillas
from tools.compare_reserved_f5 import _score_f4_snapshot
from tools.decision import MARGEN as F4_MARGIN, UMBRAL as F4_THRESHOLD
from tools.f5 import PROFILE_PATH, puntuar as puntuar_f5
from tools.resources import CONFIG

CORPUS = ROOT / "validation/narrative-v1"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_read(root: Path, relative: str) -> bytes:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("ruta fuera de la raíz: " + relative)
    return path.read_bytes()


def _verify() -> tuple[dict, dict, list[dict]]:
    lock_path = CORPUS / "candidate-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    protocol_raw = (CORPUS / "protocol.json").read_bytes()
    selection_raw = (CORPUS / "selection-lock.json").read_bytes()
    manifest_raw = (CORPUS / "reserved/manifest.jsonl").read_bytes()
    if sha(protocol_raw) != lock["protocol_sha256"]:
        raise ValueError("cambió el protocolo después de congelar el candidato")
    if sha(selection_raw) != lock["selection_lock_sha256"]:
        raise ValueError("cambió la selección después de congelar el candidato")
    if sha(manifest_raw) != lock["reserved_manifest_sha256"]:
        raise ValueError("cambió el manifiesto reservado después de congelarlo")
    for relative, expected in lock["f5_detector_sources"].items():
        if sha(_safe_read(ROOT, relative)) != expected:
            raise ValueError("cambió la fuente F5 congelada: " + relative)
    for relative, expected in lock["selection_and_evaluator_sources"].items():
        if sha(_safe_read(ROOT, relative)) != expected:
            raise ValueError("cambió la selección/evaluador congelado: " + relative)
    old_protocol_raw = (ROOT / "validation/external-v1/protocol.json").read_bytes()
    if sha(old_protocol_raw) != lock["f4_external_protocol_sha256"]:
        raise ValueError("cambió el protocolo de la baseline F4")
    old_protocol = json.loads(old_protocol_raw)
    baseline = (ROOT / lock["f4_baseline_root"]).resolve()
    if not baseline.is_relative_to(ROOT):
        raise ValueError("ruta de baseline F4 fuera del repositorio")
    for relative, expected in old_protocol["frozen_detector"].items():
        if sha(_safe_read(baseline, relative)) != expected:
            raise ValueError("cambió la baseline F4 congelada: " + relative)
    rows = [json.loads(line) for line in manifest_raw.decode("utf-8").splitlines()]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("manifiesto vacío o ids duplicados")
    for row in rows:
        raw = _safe_read(CORPUS, row["path"])
        if sha(raw) != row["sha256"]:
            raise ValueError("hash de texto incorrecto: " + row["id"])
        if row["label"] == "human" and row["source_date"] >= "2020-01-01":
            raise ValueError("la reserva incluye texto humano posterior a 2019")
    return lock, json.loads(protocol_raw), rows


def summarize(cases: list[dict], method: str) -> dict:
    counts = Counter()
    insuff = Counter()
    for case in cases:
        label = case["label"]
        prediction = case[method]["prediction"]
        score = case[method]["score"]
        counts["n"] += 1
        counts["n_ai" if label == "ai" else "n_human"] += 1
        if prediction == "abstencion":
            counts["abstain_ai" if label == "ai" else "abstain_human"] += 1
            counts["abstain_insufficient" if score is None else "abstain_band"] += 1
        elif label == "ai":
            counts["tp" if prediction == "ia" else "fn"] += 1
        else:
            counts["fp" if prediction == "ia" else "tn"] += 1
        insuff.update(case[method]["insufficient"])
    nh, ni = counts["n_human"], counts["n_ai"]
    decided_h = nh - counts["abstain_human"]
    decided_i = ni - counts["abstain_ai"]
    ratio = lambda a, b: a / b if b else None
    return {
        "counts": {key: counts[key] for key in (
            "n", "n_human", "n_ai", "tp", "fn", "fp", "tn", "abstain_human",
            "abstain_ai", "abstain_band", "abstain_insufficient")},
        "metrics": {
            "human_fp_on_all_humans": ratio(counts["fp"], nh),
            "human_decision_coverage": ratio(decided_h, nh),
            "ai_tp_on_all_ai": ratio(counts["tp"], ni),
            "ai_decision_coverage": ratio(decided_i, ni),
            "score_coverage": ratio(counts["n"] - counts["abstain_insufficient"], counts["n"]),
        },
        "insufficient_checks": dict(sorted(insuff.items())),
    }


def _grouped(cases: list[dict], method: str, key: str) -> dict:
    return {group: summarize([case for case in cases if case[key] == group], method)
            for group in sorted({case[key] for case in cases})}


def evaluate(output: Path | None = None) -> dict:
    if (output or CORPUS / "results.json").exists():
        raise ValueError("ya existe resultado de la reserva; no se repite ni se retoca en este lock")
    lock, protocol, rows = _verify()
    baseline = (ROOT / lock["f4_baseline_root"]).resolve()
    f4 = _score_f4_snapshot(rows, CORPUS, baseline)
    lexicon, seeds = _cargar_lexicon(CONFIG), _cargar_semillas()
    cases = []
    for row in rows:
        text = _safe_read(CORPUS, row["path"]).decode("utf-8")
        f5r = puntuar_f5(text, lexicon, seeds)
        cases.append({
            "id": row["id"], "label": row["label"], "panel": row["panel"],
            "group": row["group"], "author_or_model": row["author_or_model"],
            "genre": row.get("genre"), "prompt_id": row.get("prompt_id"),
            "sha256": row["sha256"],
            "f4": f4[row["id"]],
            "f5": {"score": f5r["indice_llm"], "prediction": f5r["predicho"],
                   "insufficient": f5r["checks_insuficientes"], "n_tokens": f5r["n_tokens"]},
        })
    human = [case for case in cases if case["label"] == "human"]
    ai = [case for case in cases if case["label"] == "ai"]
    by_checkpoint = _grouped(ai, "f5", "author_or_model")
    by_family = _grouped(ai, "f5", "group")
    by_genre = _grouped(human, "f5", "genre")
    gates = protocol["promotion_gates"]
    human_f5 = summarize(human, "f5")["metrics"]
    checkpoint_checks = {name: data["metrics"]["ai_tp_on_all_ai"] >= gates["ai_true_positive_rate_min_per_checkpoint"]
                         for name, data in by_checkpoint.items()}
    family_checks = {name: data["metrics"]["ai_tp_on_all_ai"] >= gates["ai_true_positive_rate_min_per_base_family"]
                     for name, data in by_family.items()}
    gate_results = {
        "human_false_positive_rate": human_f5["human_fp_on_all_humans"] <= gates["human_false_positive_rate_on_all_humans_max"],
        "human_decision_coverage": human_f5["human_decision_coverage"] >= gates["human_decision_coverage_min"],
        "ai_per_checkpoint": checkpoint_checks,
        "ai_per_base_family": family_checks,
    }
    passed = all((gate_results["human_false_positive_rate"], gate_results["human_decision_coverage"],
                  *checkpoint_checks.values(), *family_checks.values()))
    result = {
        "id": "narrative-v1-reserved-evaluation",
        "status": "f5_promoted_by_prespecified_gates" if passed else "f5_not_promoted_gates_failed",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_lock_sha256": sha((CORPUS / "candidate-lock.json").read_bytes()),
        "selection_lock_sha256": sha((CORPUS / "selection-lock.json").read_bytes()),
        "reserved_manifest_sha256": sha((CORPUS / "reserved/manifest.jsonl").read_bytes()),
        "reserved_n": len(cases),
        "detectors": {
            "f4": {"version": "f4-integridad", "threshold": F4_THRESHOLD, "margin": F4_MARGIN},
            "f5": json.loads(PROFILE_PATH.read_text(encoding="utf-8")),
        },
        "overall": {"f4": summarize(cases, "f4"), "f5": summarize(cases, "f5")},
        "human_by_genre_f5": by_genre,
        "ai_by_checkpoint": {name: {"f4": summarize([c for c in ai if c["author_or_model"] == name], "f4"), "f5": data}
                             for name, data in by_checkpoint.items()},
        "ai_by_base_family": {name: {"f4": summarize([c for c in ai if c["group"] == name], "f4"), "f5": data}
                              for name, data in by_family.items()},
        "promotion_gates": gates,
        "gate_results_f5": gate_results,
        "limitations": protocol["known_limits"],
        "reserved_set_read": True,
        "retuned_after_reserved": False,
        "cases": cases,
    }
    destination = output or CORPUS / "results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8", newline="\n")
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CORPUS / "results.json")
    args = parser.parse_args(argv)
    result = evaluate(args.output.resolve())
    print(json.dumps({
        "status": result["status"], "n": result["reserved_n"],
        "overall_f4": result["overall"]["f4"]["metrics"],
        "overall_f5": result["overall"]["f5"]["metrics"],
        "gate_results_f5": result["gate_results_f5"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
