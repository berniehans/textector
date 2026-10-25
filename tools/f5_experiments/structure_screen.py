"""Nested, group-held-out screen of frozen Spanish prose-structure features.

Reads only the explicit F5 development manifest and manual language labels.
Refuses to overwrite outputs and fails closed if any text path escapes the
development text directory. Never discovers or reads reserved data.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "validation/f5-narrative-experiment-v1"
MANIFEST = EXP / "factorial-development-manifest.jsonl"
LABELS = EXP / "language-audit-labels.jsonl"
OUT = ROOT / "validation/f5-structure-screen-v1"
PROTOCOL = ROOT / "docs/f5-structure-screen-v1.md"
PROFILES = ("M0_B0", "M1_B0_length", "M2_B0_length_structure")
STRUCTURAL_FEATURES = (
    "sentence_mean", "sentence_median", "sentence_sd", "sentence_cv",
    "sentences_per_100_tokens", "word_chars_mean", "word_chars_sd",
    "comma_per_100", "semicolon_per_100", "colon_per_100",
    "dash_per_100", "question_exclamation_per_100", "ellipsis_per_100",
    "connectors_per_100",
)
CONNECTORS = frozenset(("ademas además aunque asi así asimismo bien como consecuentemente dado debido "
    "donde durante efectivamente entonces entre finalmente luego mientras ni o obstante "
    "pero porque pues sin sino tambien también todavia todavía tras y ya primero despues después antes encima "
    "debajo alrededor incluso excepto salvo quiza quizá ahora siempre nunca").split())
PUNCTUATION = {
    "comma_per_100": re.compile(r","),
    "semicolon_per_100": re.compile(r";"),
    "colon_per_100": re.compile(r":"),
    "dash_per_100": re.compile(r"[—–-]"),
    "question_exclamation_per_100": re.compile(r"[¿?¡!]"),
    "ellipsis_per_100": re.compile(r"(?:…|\.\.\.)"),
}
N_OUTER = 5
N_INNER = 4
BOOTSTRAPS = 2000
BOOTSTRAP_SEED = 25102026


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def safe_dev_text(relative: str) -> Path:
    base = (ROOT / "validation/narrative-v1/development/texts").resolve()
    p = (ROOT / "validation/narrative-v1" / relative).resolve()
    if not p.is_relative_to(base) or "reserved" in {part.casefold() for part in p.parts}:
        raise ValueError(f"text path outside explicit development allowlist: {relative}")
    return p


def get_features(text: str, base_score: float) -> dict[str, float]:
    from tools.textector_core import normalize_text, split_sentences, tokenize

    clean = re.sub(r"\s+", " ", normalize_text(text)).strip()
    tokens = tokenize(clean)
    if not tokens:
        raise ValueError("empty text after normalization")
    n = len(tokens)
    clean_bytes = len(" ".join(tokens).encode("utf-8"))
    spans = split_sentences(clean)
    sent_lengths = [len(tokenize(span.text)) for span in spans]
    sent_lengths = [n for n in sent_lengths if n > 0]
    if not sent_lengths:
        sent_lengths = [n]
    mean_sent = statistics.fmean(sent_lengths)
    sd_sent = statistics.pstdev(sent_lengths) if len(sent_lengths) > 1 else 0.0
    word_lengths = [len(t) for t in tokens]
    features = {
        "b0_score": float(base_score),
        "log_tokens": math.log(max(1, n)),
        "log_clean_bytes": math.log(max(1, clean_bytes)),
        "sentence_mean": mean_sent,
        "sentence_median": float(statistics.median(sent_lengths)),
        "sentence_sd": sd_sent,
        "sentence_cv": sd_sent / mean_sent if mean_sent else 0.0,
        "sentences_per_100_tokens": len(sent_lengths) * 100.0 / n,
        "word_chars_mean": statistics.fmean(word_lengths),
        "word_chars_sd": statistics.pstdev(word_lengths) if len(word_lengths) > 1 else 0.0,
    }
    for name, pattern in PUNCTUATION.items():
        features[name] = len(pattern.findall(clean)) * 100.0 / n
    features["connectors_per_100"] = sum(token in CONNECTORS for token in tokens) * 100.0 / n
    return features


def fold_assignment(rows: list[dict[str, Any]], group_key: str, nfold: int) -> dict[str, int]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[group_key])].append(row)
    if len(groups) < nfold:
        raise ValueError(f"only {len(groups)} groups for {nfold} folds: {group_key}")
    # Largest groups first; stable hash breaks ties. Greedily balance row load.
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]),
                    hashlib.sha256(("structure-v1:" + kv[0]).encode()).hexdigest()))
    fold_load = [0] * nfold
    group_fold: dict[str, int] = {}
    for key, members in ranked:
        target = min(range(nfold), key=lambda i: (fold_load[i], i))
        group_fold[key] = target
        fold_load[target] += len(members)
    return {str(row["id"]): group_fold[str(row[group_key])] for row in rows}


def row_weights(rows: list[dict[str, Any]]) -> np.ndarray:
    human_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r["label"] == "human":
            human_counts[str(r["human_group"])] += 1
    vals = [1.0 / human_counts[str(r["human_group"])] if r["label"] == "human"
            else float(r["sampling_weight"]) for r in rows]
    w = np.asarray(vals, dtype=float)
    for label in ("human", "ai"):
        ix = np.asarray([r["label"] == label for r in rows])
        if ix.any():
            w[ix] /= w[ix].sum()
    return w


def matrix(rows: list[dict[str, Any]], profile: str) -> tuple[np.ndarray, list[str]]:
    if profile == "M0_B0":
        names = ["b0_score"]
    elif profile == "M1_B0_length":
        names = ["b0_score", "log_tokens", "log_clean_bytes"]
    elif profile == "M2_B0_length_structure":
        names = ["b0_score", "log_tokens", "log_clean_bytes", *STRUCTURAL_FEATURES]
    else:
        raise ValueError(profile)
    return np.asarray([[float(row["features"][name]) for name in names] for row in rows]), names


def fit_logistic(x: np.ndarray, y: np.ndarray, sample_weights: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    sd = x.std(axis=0)
    sd[sd < 1e-12] = 1.0
    z = np.clip((x - mean) / sd, -10, 10)
    z = np.column_stack([np.ones(len(z)), z])
    # Balanced objective. Apply design weights, then equalize class mass.
    w = sample_weights.copy()
    for cls in (0, 1):
        mask = y == cls
        if not mask.any():
            raise ValueError("a training fold has no class")
        w[mask] /= w[mask].sum()
        w[mask] *= 0.5
    beta = np.zeros(z.shape[1], dtype=float)
    reg = 1.0 / max(1, len(y))  # fixed C=1 logistic L2 convention
    for _ in range(6000):
        logits = np.clip(z @ beta, -30, 30)
        p = 1.0 / (1.0 + np.exp(-logits))
        grad = z.T @ (w * (p - y))
        grad[1:] += reg * beta[1:]
        step = 0.12 / (1.0 + reg)
        change = step * grad
        beta -= change
        if np.max(np.abs(change)) < 1e-8:
            break
    return beta, mean, sd


def predict(model: tuple[np.ndarray, np.ndarray, np.ndarray], x: np.ndarray) -> np.ndarray:
    beta, mean, sd = model
    z = np.clip((x - mean) / sd, -10, 10)
    z = np.column_stack([np.ones(len(z)), z])
    logits = np.clip(z @ beta, -30, 30)
    return 1.0 / (1.0 + np.exp(-logits))


def weighted_auc(y: np.ndarray, scores: np.ndarray, weights: np.ndarray) -> float | None:
    pos, neg = y == 1, y == 0
    if not pos.any() or not neg.any():
        return None
    sp, sn = scores[pos], scores[neg]
    wp, wn = weights[pos], weights[neg]
    comp = (sp[:, None] > sn[None, :]).astype(float) + 0.5 * (sp[:, None] == sn[None, :])
    return float((comp * wp[:, None] * wn[None, :]).sum() / (wp.sum() * wn.sum()))


def operating_cutoff(rows: list[dict[str, Any]], probs: np.ndarray) -> float:
    y = np.asarray([r["label"] == "ai" for r in rows], dtype=int)
    weights = row_weights(rows)
    human = y == 0
    candidates = sorted(set(float(x) for x in probs[human]))
    candidates = [0.0, *candidates, 1.0000000001]
    feasible: list[tuple[float, float]] = []
    for cut in candidates:
        pred = probs >= cut
        fp = float(weights[human][pred[human]].sum() / weights[human].sum())
        tp = float(weights[y == 1][pred[y == 1]].sum() / weights[y == 1].sum())
        if fp <= 0.05 + 1e-12:
            feasible.append((tp, cut))
    if not feasible:
        raise RuntimeError("no threshold satisfies the 5% inner-training FP constraint")
    return max(feasible, key=lambda z: (z[0], z[1]))[1]


def oof_scores(rows: list[dict[str, Any]], profile: str, nfold: int, group_key: str) -> dict[str, float]:
    assignment = fold_assignment(rows, group_key, nfold)
    out: dict[str, float] = {}
    for fold in range(nfold):
        train = [r for r in rows if assignment[str(r["id"])] != fold]
        test = [r for r in rows if assignment[str(r["id"])] == fold]
        xtr, _ = matrix(train, profile)
        xte, _ = matrix(test, profile)
        ytr = np.asarray([r["label"] == "ai" for r in train], dtype=int)
        model = fit_logistic(xtr, ytr, row_weights(train))
        for row, p in zip(test, predict(model, xte)):
            out[str(row["id"])] = float(p)
    return out


def nested_predictions(rows: list[dict[str, Any]], profile: str) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    outer_h = fold_assignment([r for r in rows if r["label"] == "human"], "human_group", N_OUTER)
    outer_a = fold_assignment([r for r in rows if r["label"] == "ai"], "prompt_id", N_OUTER)
    outer = {**outer_h, **outer_a}
    preds: dict[str, dict[str, float]] = {}
    cuts: dict[str, float] = {}
    for fold in range(N_OUTER):
        train = [r for r in rows if outer[str(r["id"])] != fold]
        test = [r for r in rows if outer[str(r["id"])] == fold]
        inner_h = fold_assignment([r for r in train if r["label"] == "human"], "human_group", N_INNER)
        inner_a = fold_assignment([r for r in train if r["label"] == "ai"], "prompt_id", N_INNER)
        inner = {**inner_h, **inner_a}
        calib: dict[str, float] = {}
        for inner_fold in range(N_INNER):
            inner_train = [r for r in train if inner[str(r["id"])] != inner_fold]
            inner_valid = [r for r in train if inner[str(r["id"])] == inner_fold]
            xtr, _ = matrix(inner_train, profile)
            xv, _ = matrix(inner_valid, profile)
            y = np.asarray([r["label"] == "ai" for r in inner_train], dtype=int)
            mdl = fit_logistic(xtr, y, row_weights(inner_train))
            for r, p in zip(inner_valid, predict(mdl, xv)):
                calib[str(r["id"])] = float(p)
        train_sorted = sorted(train, key=lambda r: str(r["id"]))
        cut = operating_cutoff(train_sorted, np.asarray([calib[str(r["id"])] for r in train_sorted]))
        xtr, _ = matrix(train, profile)
        xt, _ = matrix(test, profile)
        y = np.asarray([r["label"] == "ai" for r in train], dtype=int)
        mdl = fit_logistic(xtr, y, row_weights(train))
        for r, p in zip(test, predict(mdl, xt)):
            preds[str(r["id"])] = {"probability": float(p), "prediction_ai": float(p) >= cut,
                                    "outer_fold": fold}
        cuts[str(fold)] = cut
    return preds, cuts


def _rate(cases: list[dict[str, Any]], predicate) -> float | None:
    den = sum(float(c["sampling_weight"]) for c in cases)
    return sum(float(c["sampling_weight"]) for c in cases if predicate(c)) / den if den else None


def summarize(rows: list[dict[str, Any]], predictions: dict[str, dict[str, float]]) -> dict[str, Any]:
    cases = []
    for row in rows:
        p = predictions[str(row["id"])]
        cases.append({**row, **p})
    ai = [r for r in cases if r["label"] == "ai"]
    human = [r for r in cases if r["label"] == "human"]
    y = np.asarray([r["label"] == "ai" for r in cases], dtype=int)
    s = np.asarray([r["probability"] for r in cases])
    w = np.asarray([r["sampling_weight"] for r in cases], dtype=float)
    per_source = {}
    for src in sorted({r["checkpoint"] for r in ai}):
        subset = [r for r in ai if r["checkpoint"] == src]
        per_source[src] = {"n": len(subset), "prompts": len({r["prompt_id"] for r in subset}),
                           "detection": _rate(subset, lambda r: bool(r["prediction_ai"]))}
    return {
        "n": len(cases), "human_n": len(human), "human_authors": len({r["human_group"] for r in human}),
        "ai_n_manual_spanish": len(ai), "ai_prompts": len({r["prompt_id"] for r in ai}),
        "human_fp_all": _rate(human, lambda r: bool(r["prediction_ai"])),
        "human_coverage": 1.0,
        "ai_detection_weighted_all": _rate(ai, lambda r: bool(r["prediction_ai"])),
        "weighted_auc_oof": weighted_auc(y, s, w),
        "per_checkpoint": per_source,
        "fold_cutoffs": {str(f): next((r["cutoff"] for r in cases if r.get("fold_cutoff_key") == str(f)), None)
                         for f in range(N_OUTER)},
    }


def cluster_bootstrap(rows: list[dict[str, Any]], pred_by_profile: dict[str, dict[str, dict[str, float]]]) -> dict[str, Any]:
    # Descriptive cluster bootstrap over OOF predictions. Refuses to overstate
    # inferential certainty: it does not refit models inside each bootstrap.
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    out: dict[str, Any] = {}
    for metric in ("human_fp_all", "ai_detection_weighted_all"):
        key = "human_group" if metric == "human_fp_all" else "prompt_id"
        label = "human" if metric == "human_fp_all" else "ai"
        subset = [r for r in rows if r["label"] == label]
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in subset:
            groups[str(r[key])].append(r)
        names = sorted(groups)
        values: dict[str, list[float]] = {p: [] for p in pred_by_profile}
        for _ in range(BOOTSTRAPS):
            sample = [r for g in rng.choice(names, size=len(names), replace=True) for r in groups[str(g)]]
            den = sum(float(r["sampling_weight"]) for r in sample)
            if den == 0:
                continue
            for profile, pred in pred_by_profile.items():
                num = sum(float(r["sampling_weight"]) for r in sample
                          if bool(pred[str(r["id"])]["prediction_ai"]))
                values[profile].append(num / den)
        out[metric] = {p: {"lower_95": float(np.quantile(v, .05)), "upper_95": float(np.quantile(v, .95)),
                           "clusters": len(names), "status": "descriptive_cluster_bootstrap_not_certifying"}
                       for p, v in values.items() if v}
    # Paired detection delta M2-M1, resampled by prompt.
    subset = [r for r in rows if r["label"] == "ai"]
    groups = defaultdict(list)
    for r in subset:
        groups[str(r["prompt_id"])].append(r)
    names = sorted(groups)
    deltas = []
    for _ in range(BOOTSTRAPS):
        sample = [r for g in rng.choice(names, size=len(names), replace=True) for r in groups[str(g)]]
        den = sum(float(r["sampling_weight"]) for r in sample)
        if not den:
            continue
        m2 = sum(float(r["sampling_weight"]) for r in sample
                 if bool(pred_by_profile["M2_B0_length_structure"][str(r["id"])]["prediction_ai"])) / den
        m1 = sum(float(r["sampling_weight"]) for r in sample
                 if bool(pred_by_profile["M1_B0_length"][str(r["id"])]["prediction_ai"])) / den
        deltas.append(m2 - m1)
    out["ai_detection_delta_M2_minus_M1"] = {
        "estimate": summarize(subset, pred_by_profile["M2_B0_length_structure"])["ai_detection_weighted_all"] -
                    summarize(subset, pred_by_profile["M1_B0_length"])["ai_detection_weighted_all"],
        "lower_95": float(np.quantile(deltas, .05)), "upper_95": float(np.quantile(deltas, .95)),
        "clusters": len(names), "status": "descriptive_cluster_bootstrap_not_certifying",
    }
    return out


def run() -> dict[str, Any]:
    if OUT.exists():
        raise FileExistsError(f"output directory already exists; refusing overwrite: {OUT}")
    if not MANIFEST.is_file() or not LABELS.is_file() or not PROTOCOL.is_file():
        raise FileNotFoundError("frozen development manifest, manual labels, or protocol missing")
    manifest = read_jsonl(MANIFEST)
    labels = {r["id"]: r for r in read_jsonl(LABELS)}
    if not manifest or len({r["id"] for r in manifest}) != len(manifest):
        raise ValueError("empty manifest or duplicate IDs")
    rows = []
    exclusions = defaultdict(int)
    for source in manifest:
        label = source["label"]
        if label == "ai":
            audit = labels.get(source["id"])
            if not audit or audit.get("language") != "espanol":
                exclusions["ai_without_manual_spanish"] += 1
                continue
            weight = float(audit["sampling_weight"])
        elif label == "human":
            audit = {"language": "espanol", "sampling_weight": 1.0}
            weight = 1.0
        else:
            exclusions["unknown_label"] += 1
            continue
        path = safe_dev_text(source["path"])
        raw = path.read_bytes()
        if sha(raw) != source["sha256"]:
            raise ValueError(f"text hash mismatch: {source['id']}")
        text = raw.decode("utf-8")
        from tools.f5 import puntuar as score_f5
        from tools.cli import _cargar_lexicon, _cargar_semillas
        from tools.resources import CONFIG
        # Cache resources at function scope after first initialization.
        if not hasattr(run, "resources"):
            run.resources = (_cargar_lexicon(CONFIG), _cargar_semillas())
        lexicon, seeds = run.resources
        base = score_f5(text, lexicon, seeds)
        if base["indice_llm"] is None:
            exclusions["f5_insufficient"] += 1
            continue
        from tools.textector_core import tokenize
        n_tokens = base["n_tokens"]
        clean_bytes = base["n_bytes_limpios"]
        if n_tokens < 50 or clean_bytes < 150:
            exclusions["minimum_length"] += 1
            continue
        rows.append({
            "id": source["id"], "label": label,
            "checkpoint": source.get("author_or_model", "human"),
            "prompt_id": source.get("prompt_id") or "",
            "human_group": str(source.get("author_or_model") or source.get("book_id") or ""),
            "book_id": str(source.get("book_id") or ""),
            "sampling_weight": weight,
            "path": source["path"], "text_sha256": source["sha256"],
            "b0_decision": base["predicho"], "b0_score": float(base["indice_llm"]),
            "features": get_features(text, float(base["indice_llm"])),
        })
    human_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["label"] == "human":
            human_counts[row["human_group"]] += 1
    for row in rows:
        if row["label"] == "human":
            row["sampling_weight"] = 1.0 / human_counts[row["human_group"]]
    humans = [r for r in rows if r["label"] == "human"]
    ais = [r for r in rows if r["label"] == "ai"]
    if len({r["human_group"] for r in humans}) < N_OUTER or len({r["prompt_id"] for r in ais}) < N_OUTER:
        raise ValueError("insufficient independent groups for frozen 5-fold design")
    prediction_maps: dict[str, dict[str, dict[str, float]]] = {}
    cutoff_maps: dict[str, dict[str, float]] = {}
    for profile in PROFILES:
        pred, cuts = nested_predictions(rows, profile)
        prediction_maps[profile], cutoff_maps[profile] = pred, cuts
    summaries = {}
    for profile in PROFILES:
        summary = summarize(rows, prediction_maps[profile])
        summary["fold_cutoffs"] = cutoff_maps[profile]
        summaries[profile] = summary
    boot = cluster_bootstrap(rows, prediction_maps)
    b0_original = {
        "f5_threshold": 15, "f5_margin": 4,
        "f5_decision_rule": "unchanged; classifier screen is separate",
        "original_b0_fp_human": sum(r["label"] == "human" and r["b0_decision"] == "ia" for r in rows) / len(humans),
        "original_b0_coverage_human": sum(r["label"] == "human" and r["b0_decision"] != "abstencion" for r in rows) / len(humans),
        "original_b0_detection_ai_manual_spanish_weighted": _rate(
            [r for r in ais], lambda r: r["b0_decision"] == "ia"),
    }
    delta = summaries["M2_B0_length_structure"]["ai_detection_weighted_all"] - summaries["M1_B0_length"]["ai_detection_weighted_all"]
    source_deltas = {}
    for source in sorted({r["checkpoint"] for r in ais}):
        a = summaries["M2_B0_length_structure"]["per_checkpoint"].get(source, {}).get("detection")
        b = summaries["M1_B0_length"]["per_checkpoint"].get(source, {}).get("detection")
        source_deltas[source] = None if a is None or b is None else a - b
    improved_sources = sum(v is not None and v >= 0.05 for v in source_deltas.values())
    gate_point = summaries["M2_B0_length_structure"]["human_fp_all"] <= 0.05 and \
        summaries["M2_B0_length_structure"]["human_coverage"] >= 0.80 and delta >= 0.05 and improved_sources >= 6
    verdict = "candidate_for_independent_confirmation" if gate_point else "no_go_for_this_feature_family_or_insufficient"
    if not gate_point:
        # Distinguish an observed failure from uncertainty; small clusters block
        # claims of statistical falsification or certification.
        verdict = "no_go_operational_for_this_fixed_screen; population_level_conclusion_insufficient"
    OUT.mkdir(parents=True)
    result = {
        "protocol_id": "f5-structure-screen-v1", "status": "development_screen_not_confirmatory",
        "created_utc": "2026-10-25", "uses_reserved_data": False,
        "threshold_or_margin_changed": False, "f5_threshold": 15, "f5_margin": 4,
        "n_rows": len(rows), "n_human_authors": len({r["human_group"] for r in humans}),
        "n_ai_manual_spanish": len(ais), "n_ai_prompts": len({r["prompt_id"] for r in ais}),
        "n_checkpoints": len({r["checkpoint"] for r in ais}), "exclusions": dict(exclusions),
        "source_hashes": {"protocol": sha(PROTOCOL.read_bytes()), "manifest": sha(MANIFEST.read_bytes()),
                          "language_labels": sha(LABELS.read_bytes()),
                          "runner": sha(Path(__file__).read_bytes())},
        "profiles": summaries, "original_b0_fixed_decision_reference": b0_original,
        "delta_detection_M2_minus_M1_weighted": delta,
        "source_delta_detection_M2_minus_M1": source_deltas,
        "sources_improving_by_at_least_5pp": improved_sources,
        "cluster_bootstrap": boot, "operational_verdict": verdict,
        "limitations": ["15 autores humanos y 68 prompts IA producen intervalos amplios.",
                        "Las predicciones anidadas son cribado de desarrollo, no confirmación externa.",
                        "Los cortes se estiman dentro del desarrollo; no modifican el umbral/margen de F5.",
                        "Los pesos de IA corrigen el muestreo lingüístico estratificado; la extrapolación sigue limitada."],
    }
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    with (OUT / "oof-predictions.jsonl").open("w", encoding="utf-8", newline="\n") as h:
        for row in rows:
            h.write(json.dumps({"id": row["id"], "label": row["label"], "source": row["checkpoint"],
                                "author_group": row["human_group"], "prompt_id": row["prompt_id"],
                                "b0_score": row["b0_score"], "b0_decision": row["b0_decision"],
                                "features": row["features"], "predictions": {
                                    p: prediction_maps[p][str(row["id"])] for p in PROFILES}},
                               ensure_ascii=False, sort_keys=True) + "\n")
    report_lines = [
        "# Resultado del cribado estructural F5 v1", "",
        f"Estado: `{result['status']}`. Reserva leída: `False`. Umbral/margen modificados: `False`.",
        f"Casos elegibles: {len(rows)}; humanos: {len(humans)} en {result['n_human_authors']} autores; IA española manual: {len(ais)} en {result['n_ai_prompts']} prompts y {result['n_checkpoints']} fuentes.",
        "", "## Resultados OOF anidados", "",
        "| Modelo | FP humano | Cobertura humana | Detección IA ponderada | AUC OOF |",
        "|---|---:|---:|---:|---:|",
    ]
    for p in PROFILES:
        s = summaries[p]
        report_lines.append(f"| {p} | {s['human_fp_all']:.1%} | {s['human_coverage']:.1%} | {s['ai_detection_weighted_all']:.1%} | {s['weighted_auc_oof']:.3f} |")
    report_lines += ["", f"Delta M2−M1 en detección ponderada: **{delta*100:.2f} pp**; fuentes que mejoran ≥5 pp: **{improved_sources}/8**.",
                     "", "## Veredicto", "", f"`{verdict}`.",
                     "", "El resultado es un cribado de desarrollo; no autoriza promoción, no prueba imposibilidad general y no cambia el corte F5 15/4.",
                     "Los límites bootstrap por grupo se guardan en `results.json` y son descriptivos, no certificados.",
                     "", "## Integridad", "",
                     f"- SHA-256 protocolo: `{result['source_hashes']['protocol']}`",
                     f"- SHA-256 manifiesto: `{result['source_hashes']['manifest']}`",
                     f"- SHA-256 etiquetas: `{result['source_hashes']['language_labels']}`",
                     f"- SHA-256 runner: `{result['source_hashes']['runner']}`",
                     f"- Umbral y margen F5 preservados: `{result['f5_threshold']}/{result['f5_margin']}`"]
    (OUT / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    result = run()
    print(json.dumps({"output": str(OUT), "status": result["operational_verdict"],
                      "rows": result["n_rows"], "delta_M2_minus_M1": result["delta_detection_M2_minus_M1_weighted"],
                      "sources_plus_5pp": result["sources_improving_by_at_least_5pp"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
