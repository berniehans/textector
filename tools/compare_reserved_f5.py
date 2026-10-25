"""Compara F4 congelado con F5 en el holdout reservado; una única ejecución."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cli import _cargar_lexicon, _cargar_semillas
from tools.decision import MARGEN as F4_MARGIN, UMBRAL as F4_THRESHOLD, prediccion as f4_decision
from tools.f5 import PROFILE_PATH, puntuar as puntuar_f5
from tools.resources import CONFIG


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def resumen(cases: list[dict], method: str) -> dict:
    counts = Counter()
    insuff = Counter()
    for case in cases:
        score = case[method]["score"]
        pred = case[method]["prediction"]
        label = case["label"]
        counts["n"] += 1
        counts["n_ia" if label == "ia" else "n_human"] += 1
        if pred == "abstencion":
            counts["abstain_ia" if label == "ia" else "abstain_human"] += 1
            counts["abstain_insufficient" if score is None else "abstain_band"] += 1
        elif label == "ia":
            counts["tp" if pred == "ia" else "fn"] += 1
        else:
            counts["fp" if pred == "ia" else "tn"] += 1
        insuff.update(case[method]["insufficient"])
    n_i, n_h = counts["n_ia"], counts["n_human"]
    decisions_i = n_i - counts["abstain_ia"]
    decisions_h = n_h - counts["abstain_human"]
    ratio = lambda a, b: a / b if b else None
    return {
        "counts": {k: counts[k] for k in ("n", "n_ia", "n_human", "tp", "tn", "fp", "fn",
                                              "abstain_ia", "abstain_human", "abstain_band",
                                              "abstain_insufficient")},
        "metrics": {
            "score_coverage": ratio(n_i + n_h - counts["abstain_insufficient"], n_i + n_h),
            "decision_coverage_all": ratio(decisions_i + decisions_h, n_i + n_h),
            "decision_coverage_humans": ratio(decisions_h, n_h),
            "decision_coverage_ai": ratio(decisions_i, n_i),
            "sensitivity_conditional": ratio(counts["tp"], decisions_i),
            "specificity_conditional": ratio(counts["tn"], decisions_h),
            "fp_on_all_humans": ratio(counts["fp"], n_h),
            "tp_on_all_ai": ratio(counts["tp"], n_i),
        },
        "checks_insufficient": dict(sorted(insuff.items())),
    }


def _verify_lock(corpus: Path, lock_path: Path) -> tuple[dict, list[dict]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    manifest_raw = (corpus / "manifest.jsonl").read_bytes()
    select_raw = (corpus / "selection-lock.json").read_bytes()
    sources_raw = (corpus / "sources.json").read_bytes()
    if sha(manifest_raw) != lock["reserved_manifest_sha256"]:
        raise ValueError("manifiesto reservado cambió después de fijar F5")
    if sha(select_raw) != lock["selection_lock_sha256"]:
        raise ValueError("candado de selección reservado cambió")
    if sha(sources_raw) != lock["sources_sha256"]:
        raise ValueError("metadatos de fuente reservada cambiaron")
    rows = [json.loads(line) for line in manifest_raw.decode("utf-8").splitlines()]
    selection = json.loads(select_raw)
    if sha(manifest_raw) != selection["manifest_sha256"] or len(rows) != selection["n"]:
        raise ValueError("el manifiesto no coincide con el candado de selección")
    for name, expected in lock["detector_sources"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != expected:
            raise ValueError("cambió fuente F5 congelada: " + name)
    baseline = (ROOT / lock["f4_baseline_root"]).resolve()
    protocol = json.loads((ROOT / "validation/external-v1/protocol.json").read_text(encoding="utf-8"))
    for name, expected in protocol["frozen_detector"].items():
        path = (baseline / name).resolve()
        if not path.is_relative_to(baseline) or sha(path.read_bytes()) != expected:
            raise ValueError("baseline F4 no coincide con el detector congelado: " + name)
    for row in rows:
        path = (corpus / row["path"]).resolve()
        if not path.is_relative_to(corpus) or sha(path.read_bytes()) != row["sha256"]:
            raise ValueError("hash/ruta inválida: " + row["id"])
        if row["label"] == "human" and row["source_date"] >= "2020-01-01":
            raise ValueError("obra humana no anterior a 2020: " + row["id"])
    return lock, rows


def _score_f4_snapshot(rows: list[dict], corpus: Path, baseline: Path) -> dict[str, dict]:
    payload = [{"id": row["id"], "text": (corpus / row["path"]).read_text(encoding="utf-8")}
               for row in rows]
    code = r'''
import json,sys
from tools.cli import _cargar_lexicon,_cargar_semillas
from tools.pipeline import puntuar
from tools.resources import CONFIG
from tools.decision import prediccion
rows=json.load(sys.stdin)
lex, seeds = _cargar_lexicon(CONFIG), _cargar_semillas()
out={}
for row in rows:
 r=puntuar(row["text"],lex,seeds)
 out[row["id"]]={"score":r["indice_llm"],"prediction":prediccion(r["indice_llm"]),"insufficient":sorted(set(("burstiness","mattr","uniformity","cliches_es","compression"))-set(r["resultado"]))}
json.dump(out,sys.stdout,sort_keys=True)
'''
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    proc = subprocess.run([sys.executable, "-B", "-c", code], cwd=baseline, env=env,
                          input=json.dumps(payload, ensure_ascii=False), text=True,
                          encoding="utf-8", capture_output=True, check=True)
    return json.loads(proc.stdout)


def evaluate(corpus: Path, lock_path: Path, output: Path | None = None) -> dict:
    corpus = corpus.resolve()
    lock, rows = _verify_lock(corpus, lock_path)
    baseline = (ROOT / lock["f4_baseline_root"]).resolve()
    f4 = _score_f4_snapshot(rows, corpus, baseline)
    lexicon, seeds = _cargar_lexicon(CONFIG), _cargar_semillas()
    cases = []
    for row in rows:
        text = (corpus / row["path"]).read_text(encoding="utf-8")
        f5r = puntuar_f5(text, lexicon, seeds)
        cases.append({"id": row["id"], "label": row["label"], "panel": row["panel"],
                      "group": row["group"], "author_or_model": row["author_or_model"],
                      "sha256": row["sha256"],
                      "f4": f4[row["id"]],
                      "f5": {"score": f5r["indice_llm"], "prediction": f5r["predicho"],
                             "insufficient": f5r["checks_insuficientes"],
                             "n_tokens": f5r["n_tokens"], "n_bytes_clean": f5r["n_bytes_limpios"]}})
    panels = sorted({case["panel"] for case in cases})
    f4all, f5all = resumen(cases, "f4"), resumen(cases, "f5")
    f4panels = {p: resumen([c for c in cases if c["panel"] == p], "f4") for p in panels}
    f5panels = {p: resumen([c for c in cases if c["panel"] == p], "f5") for p in panels}
    gates = json.loads((corpus / "selection-lock.json").read_text(encoding="utf-8"))["promotion_gates"]
    human = f5panels["humanos_autores_nuevos"]["metrics"]
    tiny = f5panels["tiny_nuevo_shard"]["metrics"]
    iber = f5panels["iber_nuevos_prompts"]["metrics"]
    checks = {
        "FP_on_all_humans_max": human["fp_on_all_humans"] <= gates["FP_on_all_humans_max"],
        "decision_coverage_humans_min": human["decision_coverage_humans"] >= gates["decision_coverage_humans_min"],
        "tiny_TP_on_all_AI_min": tiny["tp_on_all_ai"] >= gates["tiny_TP_on_all_AI_min"],
        "portable_score_coverage_on_iber_min": iber["score_coverage"] >= gates["portable_score_coverage_on_iber_min"],
    }
    result = {
        "id": "reserved-f5-v1-consumption", "status": "promoted_by_prespecified_gates" if all(checks.values()) else "not_promoted_gates_failed",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "selection_lock_sha256": sha((corpus / "selection-lock.json").read_bytes()),
        "reserved_manifest_sha256": sha((corpus / "manifest.jsonl").read_bytes()),
        "f5_candidate_lock_sha256": sha(lock_path.read_bytes()),
        "n": len(cases), "f4_method": {"version": "f4-integridad", "threshold": F4_THRESHOLD, "margin": F4_MARGIN},
        "f5_profile": json.loads(PROFILE_PATH.read_text(encoding="utf-8")),
        "overall": {"f4": f4all, "f5": f5all},
        "panels": {p: {"f4": f4panels[p], "f5": f5panels[p]} for p in panels},
        "prespecified_promotion_gates": gates, "gate_results": checks,
        "limits": json.loads((corpus / "selection-lock.json").read_text(encoding="utf-8"))["limitations"],
        "reserved_set_read": True, "retuned_after_reserved": False,
        "cases": cases,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                     indent=2, allow_nan=False) + "\n",
                          encoding="utf-8", newline="\n")
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "validation/reserved-f5-v1")
    parser.add_argument("--candidate-lock", type=Path,
                        default=ROOT / "validation/reserved-f5-v1/candidate-lock.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "validation/reserved-f5-v1/results.json")
    args = parser.parse_args(argv)
    result = evaluate(args.corpus, args.candidate_lock, args.output)
    print(json.dumps({"status": result["status"], "n": result["n"],
                      "gate_results": result["gate_results"],
                      "panels": {p: {m: v[m]["counts"] for m in ("f4", "f5")}
                                 for p, v in result["panels"].items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
