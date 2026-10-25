"""Freeze reviewed C2-v2 seed documents and the development evaluation split."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.f5_experiments.prepare import (
    CORPUS,
    CORPUS_MANIFEST,
    DEVELOPMENT,
    EXPERIMENT,
    HUMAN_SEED_IDS,
    MIN_SEED_BYTES,
    PRIMARY_SEED_BYTES,
    ROOT,
    SEEDS_MANIFEST,
    TARGET_LENGTHS,
    _clean,
    _jsonl,
    _normalized_author,
    _safe_development_text,
    _sha,
)

AI_MANIFEST = DEVELOPMENT / "manifest-ai.jsonl"
HUMAN_MANIFEST = DEVELOPMENT / "manifest-human.jsonl"
CANDIDATES_PATH = EXPERIMENT / "c2-seed-candidates.json"
AUDIT_LABELS_PATH = EXPERIMENT / "language-audit-labels.jsonl"
SEED_LABELS_PATH = EXPERIMENT / "c2-seed-language-review.jsonl"
LOCK_PATH = EXPERIMENT / "c2-seed-lock.json"
SCORING_MANIFEST_PATH = EXPERIMENT / "factorial-development-manifest.jsonl"


def _unique_by_id(rows: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    out = {row["id"]: row for row in rows}
    if len(out) != len(rows):
        raise ValueError(f"duplicate IDs in {name}")
    return out


def _safe_human_source(seed_id: str) -> Path:
    if seed_id not in HUMAN_SEED_IDS:
        raise ValueError(f"human seed ID not allowlisted: {seed_id}")
    base = (ROOT / "corpus/human").resolve()
    path = (base / f"{seed_id}.txt").resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"human seed escapes allowlist: {seed_id}")
    return path


def freeze() -> dict[str, Any]:
    if LOCK_PATH.exists() or SCORING_MANIFEST_PATH.exists():
        raise FileExistsError("C2-v2 lock already exists; refusing to overwrite")
    if not all(path.is_file() for path in (CANDIDATES_PATH, AUDIT_LABELS_PATH, SEED_LABELS_PATH)):
        raise FileNotFoundError("prepare outputs or manual C2 language review are missing")

    candidates_doc = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    candidates = candidates_doc["candidate_rows"]
    candidate_by_id = _unique_by_id(candidates, "candidate queue")
    seed_reviews = _jsonl(SEED_LABELS_PATH)
    review_by_id = _unique_by_id(seed_reviews, "manual C2 language review")
    if any(row.get("language") not in {"espanol", "mixto", "ingles"} for row in seed_reviews):
        raise ValueError("invalid C2 manual language label")
    if not set(review_by_id) <= candidate_by_id.keys():
        raise ValueError("manual C2 language review contains IDs outside the frozen queue")

    selected_ai: list[dict[str, Any]] = []
    by_checkpoint: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        by_checkpoint.setdefault(row["checkpoint"], []).append(row)
    if len(by_checkpoint) != 8:
        raise ValueError(f"expected eight checkpoints in development, found {len(by_checkpoint)}")
    for checkpoint in sorted(by_checkpoint):
        selected = next((candidate for candidate in by_checkpoint[checkpoint]
                         if review_by_id.get(candidate["id"], {}).get("language") == "espanol"), None)
        if selected is None:
            raise ValueError(f"no manually verified Spanish C2 seed for checkpoint {checkpoint}")
        review = review_by_id[selected["id"]]
        if review["checkpoint"] != checkpoint or review["prompt_id"] != selected["prompt_id"]:
            raise ValueError(f"manual language review metadata mismatch for {selected['id']}")
        path = _safe_development_text(selected["path"])
        if _sha(path.read_bytes()) != selected["sha256"]:
            raise ValueError(f"AI seed hash changed: {selected['id']}")
        clean_bytes = len(_clean(path.read_text(encoding="utf-8")).encode("utf-8"))
        if clean_bytes < MIN_SEED_BYTES:
            raise ValueError(f"AI seed shorter than locked length levels: {selected['id']}")
        selected_ai.append({
            **{key: selected[key] for key in (
                "id", "checkpoint", "family", "prompt_id", "generation_type", "path", "sha256"
            )},
            "clean_bytes": clean_bytes,
            "language": "espanol",
            "language_review_method": review["review_method"],
            "language_review_scope": review["scope"],
        })

    ai_prompts = [row["prompt_id"] for row in selected_ai]
    if len(set(ai_prompts)) != 8:
        raise ValueError("C2 AI seeds must come from eight distinct prompts")
    audit_labels = _jsonl(AUDIT_LABELS_PATH)
    audit_prompts = {row["prompt_id"] for row in audit_labels if row.get("prompt_id")}
    if set(ai_prompts) & audit_prompts:
        raise ValueError("C2 seed prompts overlap the manually audited language sample")

    human_candidates = candidates_doc["human_seed_rows"]
    human_by_id = _unique_by_id(human_candidates, "human C2 seed list")
    if set(human_by_id) != set(HUMAN_SEED_IDS):
        raise ValueError("human C2 seed IDs differ from the predeclared allowlist")
    seed_manifest = json.loads(SEEDS_MANIFEST.read_text(encoding="utf-8"))
    current_seed_ids = set(seed_manifest["ia"]["ids"]) | set(seed_manifest["humana"]["ids"])
    dev_humans = _jsonl(HUMAN_MANIFEST)
    dev_authors = {_normalized_author(row["author_or_model"]) for row in dev_humans}
    human_authors: set[str] = set()
    selected_human: list[dict[str, Any]] = []
    for seed_id in HUMAN_SEED_IDS:
        row = human_by_id[seed_id]
        if seed_id in current_seed_ids:
            raise ValueError(f"C2 human seed overlaps current F5 seed: {seed_id}")
        author_key = _normalized_author(row["author"])
        if author_key in dev_authors or author_key in human_authors:
            raise ValueError(f"C2 human seed author overlaps development/another seed: {seed_id}")
        path = _safe_human_source(seed_id)
        if _sha(path.read_bytes()) != row["sha256"]:
            raise ValueError(f"human seed hash changed: {seed_id}")
        clean_bytes = len(_clean(path.read_text(encoding="utf-8")).encode("utf-8"))
        if clean_bytes < MIN_SEED_BYTES:
            raise ValueError(f"human seed shorter than locked length levels: {seed_id}")
        selected_human.append({**row, "clean_bytes": clean_bytes})
        human_authors.add(author_key)

    all_dev_rows = _jsonl(CORPUS / "development/manifest.jsonl")
    seed_prompt_set = set(ai_prompts)
    scoring_rows = [row for row in all_dev_rows
                    if not (row["label"] == "ai" and row.get("prompt_id") in seed_prompt_set)]
    removed_rows = [row for row in all_dev_rows
                    if row["label"] == "ai" and row.get("prompt_id") in seed_prompt_set]
    if len(removed_rows) == 0 or {row["prompt_id"] for row in removed_rows} != seed_prompt_set:
        raise ValueError("failed to remove all eight C2 seed prompts from the evaluation panel")
    if any("reserved" in {part.casefold() for part in str(row["path"]).split("/")} for row in scoring_rows):
        raise ValueError("scoring manifest unexpectedly contains a reserved path")

    source_files = {
        "validation/narrative-v1/development/manifest-ai.jsonl": AI_MANIFEST,
        "validation/narrative-v1/development/manifest-human.jsonl": HUMAN_MANIFEST,
        "validation/narrative-v1/development/manifest.jsonl": CORPUS / "development/manifest.jsonl",
        "corpus/manifest.csv": CORPUS_MANIFEST,
        "corpus/seeds/manifest.json": SEEDS_MANIFEST,
        "validation/f5-narrative-experiment-v1/c2-seed-candidates.json": CANDIDATES_PATH,
        "validation/f5-narrative-experiment-v1/language-audit-labels.jsonl": AUDIT_LABELS_PATH,
        "validation/f5-narrative-experiment-v1/c2-seed-language-review.jsonl": SEED_LABELS_PATH,
        "config/f5-portable.json": ROOT / "config/f5-portable.json",
        "config/cliches_es.yaml": ROOT / "config/cliches_es.yaml",
        "tools/f5.py": ROOT / "tools/f5.py",
        "tools/pipeline.py": ROOT / "tools/pipeline.py",
        "tools/checks/compression.py": ROOT / "tools/checks/compression.py",
        "tools/checks/cliches_es.py": ROOT / "tools/checks/cliches_es.py",
        "tools/checks/mattr.py": ROOT / "tools/checks/mattr.py",
        "tools/scoring.py": ROOT / "tools/scoring.py",
        "tools/decision.py": ROOT / "tools/decision.py",
    }
    lock = {
        "id": "f5-narrative-experiment-v1-c2-seeds",
        "status": "data_locked_before_scoring",
        "uses_reserved_data": False,
        "scoring_started": False,
        "development_root": "validation/narrative-v1/development",
        "ai_seed_source": "public story_writing_benchmark development examples; one manually verified Spanish text per checkpoint; prompts withheld from every scored method",
        "human_seed_source": "eight distinct pre-2020 Project Gutenberg source excerpts from the predeclared local allowlist",
        "ai_seed_rows": selected_ai,
        "human_seed_rows": selected_human,
        "seed_prompt_ids_excluded_from_evaluation": sorted(seed_prompt_set),
        "seed_prompt_rows_removed": len(removed_rows),
        "evaluation_cases": len(scoring_rows),
        "evaluation_manifest_sha256": _sha(("\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in scoring_rows
        ) + "\n").encode("utf-8")),
        "seed_pairing": {
            "ai_documents": 8,
            "human_documents": 8,
            "pairing": "all 8x8 AI-human source combinations",
            "primary_clean_bytes": PRIMARY_SEED_BYTES,
            "sensitivity_clean_bytes": [length for length in TARGET_LENGTHS if length != PRIMARY_SEED_BYTES],
            "block_rule": "normalized UTF-8 prefixes; for each AI-human pair and target length, truncate both to the same largest valid UTF-8 prefix length not exceeding the target",
            "aggregation": "median of 64 paired q values; q and score are also summarized for the two sensitivity lengths, which do not enter the factorial selection",
        },
        "language_audit": {
            "manual_reviewed_n": len(audit_labels),
            "manual_language_labels_sha256": _sha(AUDIT_LABELS_PATH.read_bytes()),
            "sampling_design": "244 certainty-reviewed heuristic positives plus 160 stratified negative sample from a 1548-item frame; negative rows carry inverse inclusion-probability weights",
            "manual_ai_seed_reviews": _sha(SEED_LABELS_PATH.read_bytes()),
            "provisional_ai_rows_remain_unverified": 1388,
        },
        "source_hashes": {name: _sha(path.read_bytes()) for name, path in source_files.items()},
    }
    SCORING_MANIFEST_PATH.write_text("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in scoring_rows
    ), encoding="utf-8", newline="\n")
    LOCK_PATH.write_text(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    return {
        "lock": str(LOCK_PATH),
        "ai_seeds": len(selected_ai),
        "human_seeds": len(selected_human),
        "distinct_seed_prompts": len(seed_prompt_set),
        "removed_ai_rows": len(removed_rows),
        "scoring_cases": len(scoring_rows),
        "scoring_started": False,
        "uses_reserved_data": False,
    }


if __name__ == "__main__":
    print(json.dumps(freeze(), ensure_ascii=False, indent=2))
