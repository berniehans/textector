"""Freeze development-only labels and C2-v2 seed candidates for F5 experiments.

This module intentionally reads only the narrative-v1 development manifests,
the historical public human corpus, and redacted language-audit annotations.
It has no generic corpus-path option and never opens reserved manifests/texts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "validation/f5-narrative-experiment-v1"
CORPUS = ROOT / "validation/narrative-v1"
DEVELOPMENT = CORPUS / "development"
AI_MANIFEST = DEVELOPMENT / "manifest-ai.jsonl"
HUMAN_MANIFEST = DEVELOPMENT / "manifest-human.jsonl"
SEEDS_MANIFEST = ROOT / "corpus/seeds/manifest.json"
CORPUS_MANIFEST = ROOT / "corpus/manifest.csv"
AUDIT_DIR_DEFAULT = ROOT.parent / "narrative-analysis"
TARGET_LENGTHS = (512, 1024, 1280)
PRIMARY_SEED_BYTES = 1024
MIN_SEED_BYTES = max(TARGET_LENGTHS)
HUMAN_SEED_IDS = ("h03", "h04", "h08", "h11", "h14", "h18", "h19", "h20")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _safe_development_text(relative: str) -> Path:
    base = DEVELOPMENT.resolve()
    path = (CORPUS / relative).resolve()
    if not path.is_relative_to(base) or "reserved" in {part.casefold() for part in path.parts}:
        raise ValueError(f"manifest path escapes development allowlist: {relative}")
    return path


def _clean(text: str) -> str:
    from tools.textector_core import normalize_text, tokenize

    return " ".join(tokenize(normalize_text(text)))


def _normalized_author(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _read_audit(audit_dir: Path) -> tuple[list[dict[str, Any]], set[str], dict[str, str]]:
    """Return redacted labels, all audited prompts, and source hashes."""
    positive_path = audit_dir / "manual-reviewed244.csv"
    negative_path = audit_dir / "negative160-manual-reviewed.csv"
    if not positive_path.is_file() or not negative_path.is_file():
        raise FileNotFoundError("expected redacted-source annotations are missing")

    rows: list[dict[str, Any]] = []
    prompts: set[str] = set()
    ids: set[str] = set()
    for path, source, certain in (
        (positive_path, "heuristic-positive-census", True),
        (negative_path, "heuristic-negative-stratified-sample", False),
    ):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for source_row in csv.DictReader(handle):
                case_id = source_row["id"]
                if case_id in ids:
                    raise ValueError(f"duplicate reviewed id in audit sources: {case_id}")
                ids.add(case_id)
                label = source_row["manual_label"]
                if label not in {"espanol", "ingles", "mixto"}:
                    raise ValueError(f"unexpected manual language label: {label}")
                prompt = source_row.get("prompt_id", "")
                if prompt:
                    prompts.add(prompt)
                inclusion_probability = 1.0 if certain else float(source_row["inclusion_probability"])
                if not 0.0 < inclusion_probability <= 1.0:
                    raise ValueError(f"invalid sampling probability for {case_id}")
                rows.append({
                    "id": case_id,
                    "checkpoint": source_row.get("checkpoint") or source_row.get("author_or_model"),
                    "prompt_id": prompt,
                    "generation_type": source_row.get("generation_type", ""),
                    "language": label,
                    "audit_source": source,
                    "inclusion_probability": inclusion_probability,
                    "sampling_weight": 1.0 / inclusion_probability,
                    "sampling_stratum": "census" if certain else ":".join((
                        source_row.get("checkpoint") or source_row.get("author_or_model", ""),
                        source_row.get("generation_type", ""),
                        source_row.get("risk", ""),
                    )),
                })
    if len(rows) != 404 or len(ids) != 404:
        raise ValueError(f"expected 404 unique manual reviews, found {len(rows)}")
    return rows, prompts, {
        positive_path.name: _sha(positive_path.read_bytes()),
        negative_path.name: _sha(negative_path.read_bytes()),
    }


def prepare(audit_dir: Path = AUDIT_DIR_DEFAULT) -> dict[str, Any]:
    if EXPERIMENT.exists():
        raise FileExistsError(f"experiment lock already exists; refusing overwrite: {EXPERIMENT}")
    audit_rows, audited_prompts, audit_hashes = _read_audit(audit_dir.resolve())
    ai_rows = _jsonl(AI_MANIFEST)
    human_rows = _jsonl(HUMAN_MANIFEST)
    if not ai_rows or not human_rows:
        raise ValueError("development-only manifests must both be non-empty")

    ai_by_id = {row["id"]: row for row in ai_rows}
    if len(ai_by_id) != len(ai_rows):
        raise ValueError("duplicate AI development IDs")
    audited_ids = {row["id"] for row in audit_rows}
    if not audited_ids <= ai_by_id.keys():
        raise ValueError("manual language audit contains IDs outside AI development")

    from tools.textector_core import normalize_text, tokenize

    audit_labels = {row["id"]: row for row in audit_rows}
    candidates_by_checkpoint: dict[str, list[dict[str, Any]]] = {}
    for row in ai_rows:
        if row["id"] in audited_ids or row.get("prompt_id") in audited_prompts:
            continue
        path = _safe_development_text(row["path"])
        raw = path.read_text(encoding="utf-8")
        clean = _clean(raw)
        clean_bytes = len(clean.encode("utf-8"))
        if clean_bytes < MIN_SEED_BYTES:
            continue
        candidate = {
            "id": row["id"],
            "checkpoint": row["author_or_model"],
            "family": row["group"],
            "prompt_id": row["prompt_id"],
            "generation_type": row["generation_type"],
            "path": row["path"],
            "sha256": row["sha256"],
            "clean_bytes": clean_bytes,
            "priority": hashlib.sha256(("f5-narrative-exp-v1:" + row["id"]).encode()).hexdigest(),
        }
        candidates_by_checkpoint.setdefault(row["author_or_model"], []).append(candidate)

    selected_candidates: list[dict[str, Any]] = []
    used_prompts = set(audited_prompts)
    for checkpoint in sorted(candidates_by_checkpoint):
        available = sorted(candidates_by_checkpoint[checkpoint], key=lambda row: (row["priority"], row["id"]))
        picked = 0
        for candidate in available:
            if candidate["prompt_id"] in used_prompts:
                continue
            selected_candidates.append(candidate)
            used_prompts.add(candidate["prompt_id"])
            picked += 1
            if picked == 3:
                break
        if picked < 3:
            raise ValueError(f"fewer than three independent Spanish seed candidates for checkpoint {checkpoint}")

    # Each checkpoint contributes a short deterministic review queue. The
    # final eight seed documents are selected only after the language labels
    # for the first valid candidate per checkpoint have been recorded.
    human_corpus_rows: dict[str, dict[str, str]] = {}
    with CORPUS_MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["clase"] == "human":
                human_corpus_rows[row["id"]] = row
    current_seed_manifest = json.loads(SEEDS_MANIFEST.read_text(encoding="utf-8"))
    current_seed_ids = set(current_seed_manifest["ia"]["ids"]) | set(current_seed_manifest["humana"]["ids"])
    dev_authors = {_normalized_author(row["author_or_model"]) for row in human_rows}
    human_seed_rows = []
    used_human_authors: set[str] = set()
    for seed_id in HUMAN_SEED_IDS:
        row = human_corpus_rows.get(seed_id)
        if row is None:
            raise ValueError(f"missing human seed source {seed_id}")
        author_key = _normalized_author(row["autor_o_modelo"])
        if seed_id in current_seed_ids or author_key in dev_authors or author_key in used_human_authors:
            raise ValueError(f"human seed overlaps current seed/development author: {seed_id}")
        path = ROOT / "corpus/human" / f"{seed_id}.txt"
        clean = _clean(path.read_text(encoding="utf-8"))
        clean_bytes = len(clean.encode("utf-8"))
        if clean_bytes < MIN_SEED_BYTES:
            raise ValueError(f"human seed too short for predeclared length levels: {seed_id}")
        human_seed_rows.append({
            "id": seed_id,
            "author": row["autor_o_modelo"],
            "work": row["obra_o_tema"],
            "path": f"corpus/human/{seed_id}.txt",
            "sha256": _sha(path.read_bytes()),
            "source": row["fuente"],
            "license": row["licencia"],
            "clean_bytes": clean_bytes,
        })
        used_human_authors.add(author_key)
    if len(human_seed_rows) != 8:
        raise ValueError("C2-v2 requires eight independent human source documents")

    EXPERIMENT.mkdir(parents=True)
    labels_path = EXPERIMENT / "language-audit-labels.jsonl"
    labels_path.write_text("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit_rows
    ), encoding="utf-8", newline="\n")
    candidate_path = EXPERIMENT / "c2-seed-candidates.json"
    candidate_path.write_text(json.dumps({
        "protocol": "f5-narrative-experiment-v1",
        "selection_rule": "per checkpoint, stable SHA-256 rank; exclude audited IDs/prompts; require >=1280 clean UTF-8 bytes; review up to three candidates in rank order; no detector scores used",
        "candidate_rows": selected_candidates,
        "human_seed_rows": human_seed_rows,
        "audited_prompt_ids_sha256": _sha("\n".join(sorted(audited_prompts)).encode()),
        "source_hashes": {
            "development_ai_manifest": _sha(AI_MANIFEST.read_bytes()),
            "development_human_manifest": _sha(HUMAN_MANIFEST.read_bytes()),
            "human_corpus_manifest": _sha(CORPUS_MANIFEST.read_bytes()),
            "current_seed_manifest": _sha(SEEDS_MANIFEST.read_bytes()),
            **audit_hashes,
        },
        "target_lengths_clean_bytes": list(TARGET_LENGTHS),
        "primary_length_clean_bytes": PRIMARY_SEED_BYTES,
        "manual_ai_labels_required_before_lock": 8,
    }, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    result = {
        "experiment_dir": str(EXPERIMENT),
        "manual_labels": len(audit_rows),
        "reviewed_label_counts": {label: sum(row["language"] == label for row in audit_rows)
                                  for label in ("espanol", "mixto", "ingles")},
        "audited_prompts": len(audited_prompts),
        "candidate_rows": len(selected_candidates),
        "checkpoints": len(candidates_by_checkpoint),
        "human_seed_rows": len(human_seed_rows),
        "primary_seed_bytes": PRIMARY_SEED_BYTES,
        "sensitivity_seed_bytes": [512, 1280],
        "scoring_started": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=AUDIT_DIR_DEFAULT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.audit_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
