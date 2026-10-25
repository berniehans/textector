"""Run the locked development-only F5 narrative factorial.

This runner reads only the locked development manifest. It does not accept a
corpus path, does not discover files recursively, and fails closed on any path
outside the development allowlist. It never opens a reserved manifest or text.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any

from tools.f5_experiments.prepare import (
    CORPUS,
    DEVELOPMENT,
    EXPERIMENT,
    ROOT,
    _clean,
    _jsonl,
    _safe_development_text,
    _sha,
)

LOCK_PATH = EXPERIMENT / "c2-seed-lock.json"
SCORED_MANIFEST_PATH = EXPERIMENT / "factorial-development-manifest.jsonl"
AUDIT_LABELS_PATH = EXPERIMENT / "language-audit-labels.jsonl"
RESULTS_PATH = EXPERIMENT / "factorial-results.json"
CASE_SCORES_PATH = EXPERIMENT / "factorial-case-scores.jsonl"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 25102026
WEIGHTS = {"mattr": 0.45, "cliches_es": 0.25, "compression_positive_only": 0.30}
THRESHOLD = 15
MARGIN = 4
MATTR_MIN = 0.55
MATTR_MAX = 0.85
CLICHE_HIT_GATE = 3
COMPRESSION_NEUTRAL_Q = 0.5
SEED_LENGTHS = (512, 1024, 1280)

PROFILE_FACTORS = {
    "P000": (False, False, False),
    "P100": (True, False, False),
    "P010": (False, True, False),
    "P001": (False, False, True),
    "P110": (True, True, False),
    "P101": (True, False, True),
    "P011": (False, True, True),
    "P111": (True, True, True),
}


def _sha_file(path: Path) -> str:
    return _sha(path.read_bytes())


def _verify_lock(lock: dict[str, Any]) -> None:
    if lock.get("uses_reserved_data") is not False or lock.get("scoring_started") is not False:
        raise ValueError("invalid or already consumed development lock")
    if Path(lock.get("development_root", "")).as_posix() != "validation/narrative-v1/development":
        raise ValueError("unexpected development root")
    if len(lock.get("ai_seed_rows", [])) != 8 or len(lock.get("human_seed_rows", [])) != 8:
        raise ValueError("locked C2-v2 bank must contain eight documents per class")
    if len(set(lock.get("seed_prompt_ids_excluded_from_evaluation", []))) != 8:
        raise ValueError("locked seed prompts must be eight and distinct")
    for name, expected in lock["source_hashes"].items():
        # Every source is repo-relative and explicitly allowlisted by the
        # freeze script. No path under any reserved directory is read here.
        path = (ROOT / name).resolve() if not Path(name).is_absolute() else Path(name)
        if not path.is_file() or _sha_file(path) != expected:
            raise ValueError(f"locked source changed: {name}")
    for row in lock["ai_seed_rows"]:
        path = _safe_development_text(row["path"])
        if _sha_file(path) != row["sha256"]:
            raise ValueError(f"locked AI seed changed: {row['id']}")
    for row in lock["human_seed_rows"]:
        path = (ROOT / row["path"]).resolve()
        if not path.is_relative_to((ROOT / "corpus/human").resolve()):
            raise ValueError(f"human seed outside its allowlist: {row['id']}")
        if _sha_file(path) != row["sha256"]:
            raise ValueError(f"locked human seed changed: {row['id']}")


def _valid_prefix(raw: bytes, limit: int) -> bytes:
    block = raw[:limit]
    while block:
        try:
            block.decode("utf-8")
            return block
        except UnicodeDecodeError as exc:
            block = block[:exc.start]
    return b""


def _paired_blocks(ai_clean: str, human_clean: str, limit: int) -> tuple[str, str, int]:
    ai_prefix = _valid_prefix(ai_clean.encode("utf-8"), limit)
    human_prefix = _valid_prefix(human_clean.encode("utf-8"), limit)
    n_bytes = min(len(ai_prefix), len(human_prefix))
    if n_bytes < limit - 3:
        raise ValueError("paired UTF-8 seed block lost more than one codepoint")
    return ai_prefix[:n_bytes].decode("utf-8"), human_prefix[:n_bytes].decode("utf-8"), n_bytes


def _load_c2_bank(lock: dict[str, Any]) -> dict[int, list[tuple[str, str]]]:
    ai_clean: list[str] = []
    human_clean: list[str] = []
    for row in lock["ai_seed_rows"]:
        ai_clean.append(_clean(_safe_development_text(row["path"]).read_text(encoding="utf-8")))
    for row in lock["human_seed_rows"]:
        path = (ROOT / row["path"]).resolve()
        human_clean.append(_clean(path.read_text(encoding="utf-8")))
    bank: dict[int, list[tuple[str, str]]] = {}
    for length in SEED_LENGTHS:
        pairs = []
        for ai_text in ai_clean:
            for human_text in human_clean:
                ai_block, human_block, _ = _paired_blocks(ai_text, human_text, length)
                pairs.append((ai_block, human_block))
        if len(pairs) != 64:
            raise ValueError("C2-v2 requires all 64 AI-human seed combinations")
        bank[length] = pairs
    return bank


def _mattr_q(text: str, window: int) -> tuple[float, bool, int]:
    from tools.textector_core import tokenize

    tokens = tokenize(text)
    if len(tokens) < window:
        return 0.0, True, len(tokens)
    values = [len(set(tokens[i:i + window])) / window
              for i in range(len(tokens) - window + 1)]
    mattr = sum(values) / len(values)
    q = max(0.0, min(1.0, 1.0 - (mattr - MATTR_MIN) / (MATTR_MAX - MATTR_MIN)))
    return q, False, len(tokens)


def _median_compression_q(text: str, pairs: list[tuple[str, str]]) -> tuple[float, dict[str, Any]]:
    from tools.checks import compression
    from tools.textector_core import normalize_text, tokenize

    sample = " ".join(tokenize(normalize_text(text)))
    clean_bytes = len(sample.encode("utf-8"))
    if clean_bytes < compression.MIN_BYTES_MUESTRA:
        return 0.0, {"insufficient": True, "n_bytes_muestra": clean_bytes, "n_pairs": len(pairs)}
    sample_tokens = sample.split(" ")
    if len(sample_tokens) > compression.MAX_TOKENS:
        sample = " ".join(sample_tokens[:compression.MAX_TOKENS])
    sample_bytes = sample.encode("utf-8")
    sample_n_bytes = len(sample_bytes)
    # C2 reuses the same seed blocks for every evaluated document. Cache each
    # seed's baseline DEFLATE size; only the concatenated seed+sample depends
    # on the current document. This is algebraically identical to
    # compression._marginal and keeps the preregistered score unchanged.
    base_sizes: dict[str, int] = getattr(_median_compression_q, "_base_sizes", {})
    q_values: list[float] = []
    for seed_ia, seed_human in pairs:
        m_values = []
        for seed in (seed_ia, seed_human):
            base_size = base_sizes.get(seed)
            if base_size is None:
                base_size = compression._raw_deflate(seed.encode("utf-8"))
                base_sizes[seed] = base_size
            sep = " " if seed and sample else ""
            complete = (seed + sep).encode("utf-8") + sample_bytes
            m_values.append((compression._raw_deflate(complete) - base_size) / sample_n_bytes)
        m_ai, m_human = m_values
        delta = m_ai - m_human
        q_values.append(max(0.0, min(1.0, 0.5 - delta / compression.ESCALA_DELTA)))
    setattr(_median_compression_q, "_base_sizes", base_sizes)
    return statistics.median(q_values), {
        "insufficient": False,
        "n_bytes_muestra": clean_bytes,
        "n_pairs": len(q_values),
        "q_min": min(q_values),
        "q_max": max(q_values),
        "q_median": statistics.median(q_values),
    }


def _decision(score: int | None) -> str:
    lower, upper = THRESHOLD - MARGIN, THRESHOLD + MARGIN
    if score is None or lower <= score <= upper:
        return "abstencion"
    return "ia" if score > upper else "humano"


def _base_variant_metrics(text: str, lexicon: list[Any], seeds: tuple[str, str]) -> dict[str, Any]:
    """Compute the factor-invariant checks once for one evaluation text."""
    from tools.checks import cliches_es, compression, mattr
    from tools.textector_core import tokenize

    return {
        "n_tokens": len(tokenize(text)),
        "mattr": mattr.check(text),
        "cliches": cliches_es.check(text, lexicon=lexicon),
        "compression": compression.check(text, seed_ia=seeds[0], seed_hum=seeds[1]),
    }


def _score_variant(
    text: str,
    lexicon: list[Any],
    seeds: tuple[str, str],
    factors: tuple[bool, bool, bool],
    c2_q_by_length: dict[int, float],
    c2_length: int = 1024,
    base_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from tools.checks import cliches_es, compression, mattr

    use_l2, use_c2, use_m100 = factors
    if base_metrics is None:
        base_metrics = _base_variant_metrics(text, lexicon, seeds)
    n_tokens = base_metrics["n_tokens"]
    r_mattr = base_metrics["mattr"]
    r_cliche = base_metrics["cliches"]
    r_compression = base_metrics["compression"]

    if use_m100 and n_tokens >= 100:
        m100 = base_metrics.get("m100")
        if m100 is None:
            m100 = _mattr_q(text, 100)
            base_metrics["m100"] = m100
        q_mattr, mattr_insufficient, _ = m100
        mattr_window = 100
    else:
        q_mattr = float(r_mattr.normalizado)
        mattr_insufficient = r_mattr.insufficient
        mattr_window = 50

    density = float(r_cliche.valor_bruto.get("densidad_ponderada_por_1000", 0.0))
    hits = int(r_cliche.valor_bruto.get("n_hits_total", 0))
    lex_scale = 2.5 if use_l2 else 25.0
    q_lex = min(1.0, max(0.0, density / lex_scale)) * min(1.0, hits / CLICHE_HIT_GATE)
    q_comp = c2_q_by_length[c2_length] if use_c2 else float(r_compression.normalizado)
    q_comp_positive = min(1.0, max(0.0, (q_comp - COMPRESSION_NEUTRAL_Q) / (1.0 - COMPRESSION_NEUTRAL_Q)))

    insufficient: list[str] = []
    if n_tokens < 50 or mattr_insufficient:
        insufficient.append("mattr")
    if n_tokens < cliches_es.MIN_TOKENS or r_cliche.insufficient:
        insufficient.append("cliches_es")
    if r_compression.insufficient:
        insufficient.append("compression")
    contributions = {
        "mattr": WEIGHTS["mattr"] * q_mattr * 100.0,
        "cliches_es": WEIGHTS["cliches_es"] * q_lex * 100.0,
        "compression_positive_only": WEIGHTS["compression_positive_only"] * q_comp_positive * 100.0,
    }
    score = None if insufficient else int(round(sum(contributions.values())))
    return {
        "score": score,
        "prediction": _decision(score),
        "q": {"mattr": q_mattr, "cliches_es": q_lex, "compression": q_comp,
              "compression_positive_only": q_comp_positive},
        "contributions": contributions,
        "insufficient": sorted(set(insufficient)),
        "n_tokens": n_tokens,
        "mattr_window": mattr_window,
        "density_per_1000": density,
        "cliche_hits": hits,
    }


def _summarize(cases: list[dict[str, Any]], method: str, weights: dict[str, float] | None = None) -> dict[str, Any]:
    counts = defaultdict(float)
    labels = {"human": "human", "ai": "ai"}
    for case in cases:
        label = labels[case["label"]]
        weight = (weights or {}).get(case["id"], 1.0)
        prediction = case[method]["prediction"]
        counts["n_" + label] += weight
        if prediction == "abstencion":
            counts["abstain_" + label] += weight
            counts["abstain_insufficient" if case[method].get("score") is None else "abstain_band"] += weight
        elif label == "ai":
            counts["tp" if prediction == "ia" else "fn"] += weight
        else:
            counts["fp" if prediction == "ia" else "tn"] += weight
    n_h, n_ai = counts["n_human"], counts["n_ai"]
    div = lambda a, b: a / b if b else None
    return {
        "counts": {key: counts[key] for key in (
            "n_human", "n_ai", "tp", "fn", "fp", "tn", "abstain_human", "abstain_ai",
            "abstain_band", "abstain_insufficient")},
        "metrics": {
            "human_fp_on_all_humans": div(counts["fp"], n_h),
            "human_decision_coverage": div(n_h - counts["abstain_human"], n_h),
            "ai_detection_on_all_ai": div(counts["tp"], n_ai),
            "ai_decision_coverage": div(n_ai - counts["abstain_ai"], n_ai),
        },
    }


def _group_summary(cases: list[dict[str, Any]], method: str, key: str,
                   weights: dict[str, float] | None = None) -> dict[str, Any]:
    return {str(group): _summarize([case for case in cases if str(case.get(key)) == str(group)], method, weights)
            for group in sorted({case.get(key) for case in cases}, key=lambda x: str(x))}


def _bootstrap_cluster_interval(cases: list[dict[str, Any]], method: str, outcome: str,
                                cluster_key: str, weights: dict[str, float] | None = None,
                                replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    """Exploratory one-sided cluster percentile bounds; never a gate certificate."""
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        clusters[str(case[cluster_key])].append(case)
    keys = sorted(clusters)
    if len(keys) < 10:
        return {"lower_95": None, "upper_95": None, "n_clusters": len(keys),
                "status": "too_few_clusters"}
    rng = random.Random(BOOTSTRAP_SEED)
    vals: list[float] = []
    for _ in range(replicates):
        sample = [case for key in (rng.choice(keys) for _ in keys) for case in clusters[key]]
        if outcome == "human_fp":
            selected = [c for c in sample if c["label"] == "human"]
            metric = _summarize(selected, method, weights)["metrics"]["human_fp_on_all_humans"]
        elif outcome == "human_coverage":
            selected = [c for c in sample if c["label"] == "human"]
            metric = _summarize(selected, method, weights)["metrics"]["human_decision_coverage"]
        elif outcome == "ai_detection":
            selected = [c for c in sample if c["label"] == "ai"]
            metric = _summarize(selected, method, weights)["metrics"]["ai_detection_on_all_ai"]
        else:
            raise ValueError(outcome)
        if metric is not None:
            vals.append(float(metric))
    vals.sort()
    if len(vals) < replicates * 0.95:
        return {"lower_95": None, "upper_95": None, "n_clusters": len(keys),
                "status": "unstable_bootstrap"}
    lo = vals[int(0.05 * (len(vals) - 1))]
    hi = vals[int(0.95 * (len(vals) - 1))]
    return {"lower_95": lo, "upper_95": hi, "n_clusters": len(keys),
            "status": "exploratory_cluster_bootstrap_not_certifying"}


def run() -> dict[str, Any]:
    if RESULTS_PATH.exists() or CASE_SCORES_PATH.exists():
        raise FileExistsError("experiment results already exist; refusing to overwrite")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    _verify_lock(lock)
    scoring_rows = _jsonl(SCORED_MANIFEST_PATH)
    if len(scoring_rows) != lock["evaluation_cases"]:
        raise ValueError("scoring manifest size differs from frozen lock")
    if _sha(("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in scoring_rows) + "\n").encode()) != lock["evaluation_manifest_sha256"]:
        raise ValueError("scoring manifest hash differs from frozen lock")

    from tools.cli import _cargar_lexicon, _cargar_semillas
    from tools.decision import prediccion as f4_decision
    from tools.f5 import puntuar as puntuar_f5
    from tools.pipeline import puntuar as puntuar_f4
    from tools.resources import CONFIG

    lexicon, seeds = _cargar_lexicon(CONFIG), _cargar_semillas()
    ai_seed_rows = lock["ai_seed_rows"]
    human_seed_rows = lock["human_seed_rows"]
    bank = _load_c2_bank(lock)
    audit_rows = _jsonl(AUDIT_LABELS_PATH)
    audit_by_id = {row["id"]: row for row in audit_rows}
    language_weights = {row["id"]: float(row["sampling_weight"])
                        for row in audit_rows if row["language"] == "espanol"}

    # Full B0 reproduction (including the eight C2 seed prompts) is recorded
    # separately. The factorial itself uses only the locked prompt-disjoint panel.
    full_rows = _jsonl(CORPUS / "development/manifest.jsonl")
    full_cases: list[dict[str, Any]] = []
    full_f5_by_id: dict[str, dict[str, Any]] = {}
    full_f4_by_id: dict[str, dict[str, Any]] = {}
    for row in full_rows:
        path = _safe_development_text(row["path"])
        if _sha_file(path) != row["sha256"]:
            raise ValueError(f"development text hash changed: {row['id']}")
        text = path.read_text(encoding="utf-8")
        f5 = puntuar_f5(text, lexicon, seeds)
        f4 = puntuar_f4(text, lexicon, seeds)
        f4_case = {"score": f4["indice_llm"], "prediction": f4_decision(f4["indice_llm"]),
                   "insufficient": sorted(set(("burstiness", "mattr", "uniformity", "cliches_es", "compression")) - set(f4["resultado"]))}
        f5_case = {"score": f5["indice_llm"], "prediction": f5["predicho"],
                   "insufficient": f5["checks_insuficientes"], "q": f5["q_efectivos"],
                   "contributions": f5["contribuciones"], "n_tokens": f5["n_tokens"]}
        full_f5_by_id[row["id"]], full_f4_by_id[row["id"]] = f5_case, f4_case
        full_cases.append({**row, "f5": f5_case, "f4": f4_case})

    # B0 is called directly for every factorial row; new profiles change only
    # their predeclared factor and share the same input texts.
    cases: list[dict[str, Any]] = []
    base_metrics_by_id: dict[str, dict[str, Any]] = {}
    row_by_id = {row["id"]: row for row in scoring_rows}
    for row in scoring_rows:
        path = _safe_development_text(row["path"])
        text = path.read_text(encoding="utf-8")
        b0 = full_f5_by_id[row["id"]]
        f4 = full_f4_by_id[row["id"]]
        q_lengths = {}
        q_meta = {}
        for length in SEED_LENGTHS:
            q_lengths[length], q_meta[length] = _median_compression_q(text, bank[length])
        base_metrics = _base_variant_metrics(text, lexicon, seeds)
        base_metrics_by_id[row["id"]] = base_metrics
        profile_scores = {"P000": b0}
        for profile, factors in PROFILE_FACTORS.items():
            if profile == "P000":
                continue
            profile_scores[profile] = _score_variant(
                text, lexicon, seeds, factors, q_lengths, base_metrics=base_metrics)
        if (profile_scores["P000"]["score"], profile_scores["P000"]["prediction"]) != (
                b0["score"], b0["prediction"]):
            raise ValueError(f"B0 parity failure on factorial row {row['id']}")
        lang = audit_by_id.get(row["id"], {})
        cases.append({
            "id": row["id"], "label": row["label"], "panel": row.get("panel"),
            "group": row.get("group"), "author_or_model": row.get("author_or_model"),
            "book_id": row.get("book_id"), "genre": row.get("genre"),
            "prompt_id": row.get("prompt_id"), "generation_type": row.get("generation_type"),
            "sha256": row["sha256"], "manual_language": lang.get("language", "no-manual-label"),
            "sampling_weight": lang.get("sampling_weight"),
            "f4": f4, **profile_scores,
            "c2_compression_q_by_length": q_lengths,
            "c2_compression_spread_by_length": q_meta,
        })

    # Raw benchmark-language view is descriptive only; language-screened panels
    # are kept separate to avoid treating provisional Spanish as confirmed.
    full_ai = [case for case in full_cases if case["label"] == "ai"]
    full_raw_by_checkpoint = _group_summary(full_ai, "f5", "author_or_model")
    reviewed_spanish_ai = [case for case in cases if case["label"] == "ai" and case["manual_language"] == "espanol"]
    provisional_ai = [case for case in cases if case["label"] == "ai" and case["manual_language"] == "no-manual-label"]
    english_mixed_ai = [case for case in cases if case["label"] == "ai" and case["manual_language"] in {"ingles", "mixto"}]
    humans = [case for case in cases if case["label"] == "human"]

    profile_reports: dict[str, Any] = {}
    for profile in PROFILE_FACTORS:
        human_summary = _summarize(humans, profile)
        ai_all_summary = _summarize([case for case in cases if case["label"] == "ai"], profile)
        ai_provisional_summary = _summarize(provisional_ai, profile)
        ai_nonspanish_summary = _summarize(english_mixed_ai, profile)
        ai_spanish_weighted = _summarize(reviewed_spanish_ai, profile, language_weights)
        by_checkpoint_raw = _group_summary([case for case in cases if case["label"] == "ai"], profile, "author_or_model")
        by_checkpoint_reviewed = {}
        for checkpoint in sorted({case["author_or_model"] for case in reviewed_spanish_ai}):
            subset = [case for case in reviewed_spanish_ai if case["author_or_model"] == checkpoint]
            weighted = _summarize(subset, profile, language_weights)
            total_w = sum(language_weights[case["id"]] for case in subset)
            sum_w2 = sum(language_weights[case["id"]] ** 2 for case in subset)
            weighted["sampled_texts"] = len(subset)
            weighted["sampled_prompts"] = len({case["prompt_id"] for case in subset})
            weighted["effective_sample_size_kish"] = (total_w * total_w / sum_w2) if sum_w2 else 0.0
            by_checkpoint_reviewed[checkpoint] = weighted
        profile_reports[profile] = {
            "factors": {"L2": PROFILE_FACTORS[profile][0], "C2-v2": PROFILE_FACTORS[profile][1],
                        "M100-fallback50": PROFILE_FACTORS[profile][2]},
            "human_development": human_summary,
            "ai_all_benchmark_language_descriptive": ai_all_summary,
            "ai_by_checkpoint_benchmark_language_descriptive": by_checkpoint_raw,
            "ai_manually_verified_spanish_sampling_weighted": ai_spanish_weighted,
            "ai_manually_verified_spanish_by_checkpoint_weighted": by_checkpoint_reviewed,
            "ai_language_provisional_descriptive": ai_provisional_summary,
            "ai_manually_english_or_mixed_descriptive": ai_nonspanish_summary,
            "certification_status": "not_confirmatory; development sample and clustered/stratified language audit",
        }

    # The human clusters and manually reviewed Spanish AI prompt groups are
    # resampled for exploratory uncertainty only. The unequal-probability
    # language audit requires a separate confirmatory sampling design for gates.
    for profile, report in profile_reports.items():
        report["human_cluster_bootstrap_exploratory"] = {
            "fp": _bootstrap_cluster_interval(humans, profile, "human_fp", "author_or_model"),
            "coverage": _bootstrap_cluster_interval(humans, profile, "human_coverage", "author_or_model"),
        }
        report["ai_prompt_cluster_bootstrap_exploratory"] = {}
        for checkpoint in sorted({case["author_or_model"] for case in reviewed_spanish_ai}):
            subset = [case for case in reviewed_spanish_ai if case["author_or_model"] == checkpoint]
            # To bootstrap a design-weighted ratio, the same survey weights are
            # retained. This is exploratory and cannot certify the gate.
            report["ai_prompt_cluster_bootstrap_exploratory"][checkpoint] = _bootstrap_cluster_interval(
                subset, profile, "ai_detection", "prompt_id", language_weights
            )

    # H0/H1 point-estimate screen for the predeclared +5 pp improvement.
    base_by_checkpoint = profile_reports["P000"]["ai_manually_verified_spanish_by_checkpoint_weighted"]
    improvement_hypotheses = {}
    for profile in ("P100", "P010", "P001", "P110", "P101", "P011", "P111"):
        current = profile_reports[profile]["ai_manually_verified_spanish_by_checkpoint_weighted"]
        deltas = {}
        for checkpoint, base in base_by_checkpoint.items():
            base_rate = base["metrics"]["ai_detection_on_all_ai"]
            current_rate = current[checkpoint]["metrics"]["ai_detection_on_all_ai"]
            deltas[checkpoint] = None if base_rate is None or current_rate is None else current_rate - base_rate
        point_h1 = bool(deltas) and all(delta is not None and delta >= 0.05 for delta in deltas.values())
        improvement_hypotheses[profile] = {
            "H0": "no >=5 percentage-point increase in every checkpoint",
            "H1": ">=5 percentage-point increase in every checkpoint",
            "delta_detection_by_checkpoint": deltas,
            "point_estimate_supports_H1": point_h1,
            "inferential_status": "exploratory; no confirmatory claim",
        }

    gate_point_estimates: dict[str, Any] = {}
    for profile, report in profile_reports.items():
        h = report["human_development"]["metrics"]
        ai = report["ai_manually_verified_spanish_by_checkpoint_weighted"]
        point_pass = bool(ai) and (
            h["human_fp_on_all_humans"] is not None and h["human_fp_on_all_humans"] <= 0.05 and
            h["human_decision_coverage"] is not None and h["human_decision_coverage"] >= 0.80 and
            all(v["metrics"]["ai_detection_on_all_ai"] is not None and
                v["metrics"]["ai_detection_on_all_ai"] >= 0.80 for v in ai.values())
        )
        gate_point_estimates[profile] = {
            "point_estimates_pass_all_gates": point_pass,
            "confidence_bound_pass": False,
            "decision": "datos_insuficientes_para_promocion",
            "reason": "development data, 15 human author clusters, small weighted manual Spanish AI sample, no independent confirmation",
        }

    profile_for_sensitivity = "P010"
    sensitivity: dict[str, Any] = {}
    for length in (512, 1280):
        sensitivity_cases = []
        for case in cases:
            q = case["c2_compression_q_by_length"][length]
            qmap = {n: q for n in SEED_LENGTHS}
            text = _safe_development_text(
                row_by_id[case["id"]]["path"]
            ).read_text(encoding="utf-8")
            alt = _score_variant(
                text, lexicon, seeds, (False, True, False), qmap,
                c2_length=length, base_metrics=base_metrics_by_id[case["id"]])
            sensitivity_cases.append({**case, "C2_sensitivity": alt})
        human_sens = _summarize([c for c in sensitivity_cases if c["label"] == "human"], "C2_sensitivity")
        ai_verified_sens = _summarize(
            [c for c in sensitivity_cases if c["label"] == "ai" and c["manual_language"] == "espanol"],
            "C2_sensitivity", language_weights
        )
        ai_by_checkpoint_sens = _group_summary(
            [c for c in sensitivity_cases if c["label"] == "ai" and c["manual_language"] == "espanol"],
            "C2_sensitivity", "author_or_model", language_weights
        )
        sensitivity[str(length)] = {
            "human_development": human_sens,
            "ai_manually_verified_spanish_sampling_weighted": ai_verified_sens,
            "ai_manually_verified_spanish_by_checkpoint_weighted": ai_by_checkpoint_sens,
            "q_delta_vs_1024_mean": statistics.mean(
                case["c2_compression_q_by_length"][length] - case["c2_compression_q_by_length"][1024]
                for case in cases
            ) if cases else None,
            "selection_use": "sensitivity_only; not a factorial candidate",
        }

    # Freeze the exact code/input state used for this run in the output.
    code_paths = [
        ROOT / "tools/f5_experiments/prepare.py", ROOT / "tools/f5_experiments/freeze_seeds.py",
        ROOT / "tools/f5_experiments/run.py", ROOT / "tools/f5.py", ROOT / "tools/pipeline.py",
        ROOT / "tools/scoring.py", ROOT / "tools/decision.py", ROOT / "tools/checks/compression.py",
        ROOT / "tools/checks/cliches_es.py", ROOT / "tools/checks/mattr.py",
        ROOT / "config/f5-portable.json", ROOT / "config/cliches_es.yaml",
    ]
    result = {
        "id": "f5-narrative-experiment-v1-development-factorial",
        "status": "development_experiment_complete_not_confirmatory",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_id": "f5-narrative-experiment-v1",
        "uses_reserved_data": False,
        "retuned_threshold_or_margin": False,
        "threshold": THRESHOLD,
        "abstention_margin": MARGIN,
        "promotion_gates": {"human_fp_max": 0.05, "human_coverage_min": 0.80,
                            "ai_detection_min_per_checkpoint": 0.80,
                            "one_sided_confidence": 0.95,
                            "practical_improvement_min_pp": 5},
        "hypotheses": {
            "global_H0": "at least one promotion gate fails in the target population",
            "global_H1": "all gates pass by point estimates and one-sided 95% bounds for every checkpoint",
            "signal_H0": "less than a 5 pp detection increase over B0 in at least one checkpoint",
            "signal_H1": "at least a 5 pp detection increase over B0 in every checkpoint",
            "interaction_H0": "factor effects are additive on detection proportions",
            "interaction_H1": "at least one predeclared factorial interaction is nonzero",
        },
        "data": {
            "full_development_n": len(full_cases),
            "factorial_n": len(cases),
            "c2_seed_prompts_removed": len(lock["seed_prompt_ids_excluded_from_evaluation"]),
            "c2_seed_rows_removed_from_ai_panel": lock["seed_prompt_rows_removed"],
            "manual_language_reviewed_n": len(audit_rows),
            "manual_language_label_counts": {label: sum(row["language"] == label for row in audit_rows)
                                             for label in ("espanol", "mixto", "ingles")},
            "manually_verified_spanish_ai_rows_in_factorial": len(reviewed_spanish_ai),
            "provisional_ai_rows_in_factorial": len(provisional_ai),
            "english_or_mixed_ai_rows_in_factorial": len(english_mixed_ai),
            "human_author_clusters": len({case["author_or_model"] for case in humans}),
            "verified_spanish_ai_prompt_clusters": len({case["prompt_id"] for case in reviewed_spanish_ai}),
        },
        "controls": {
            "b0_full_development": _summarize(full_cases, "f5"),
            "f4_full_development": _summarize(full_cases, "f4"),
            "b0_full_ai_by_checkpoint": full_raw_by_checkpoint,
            "factorial_f4_reference": _summarize(cases, "f4"),
        },
        "factorial_profiles": profile_reports,
        "five_pp_improvement_hypotheses": improvement_hypotheses,
        "point_gate_screen": gate_point_estimates,
        "c2_seed_length_sensitivity": sensitivity,
        "statistical_note": "Cluster bootstrap bounds are exploratory only. The language-audit sample is stratified with unequal inclusion probabilities and prompt dependence; this development run cannot certify the prespecified promotion gates. Confirmation requires a new, independently sampled and sufficiently clustered corpus.",
        "lock_sha256": _sha_file(LOCK_PATH),
        "scoring_manifest_sha256": _sha_file(SCORED_MANIFEST_PATH),
        "code_hashes": {str(path.relative_to(ROOT)): _sha_file(path) for path in code_paths},
        "cases": cases,
    }
    RESULTS_PATH.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
                            encoding="utf-8", newline="\n")
    with CASE_SCORES_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    report = run()
    print(json.dumps({
        "status": report["status"], "data": report["data"],
        "controls": {key: value["metrics"] for key, value in report["controls"].items()
                     if isinstance(value, dict) and "metrics" in value},
        "point_gate_screen": report["point_gate_screen"],
        "uses_reserved_data": report["uses_reserved_data"],
    }, ensure_ascii=False, indent=2))
