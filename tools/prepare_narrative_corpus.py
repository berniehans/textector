"""Descarga, divide y fija el panel español del benchmark de relatos públicos.

Este preparador no puntúa los textos ni consulta el perfil del detector.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "validation/narrative-v1"
PROTOCOL = CORPUS / "protocol.json"
EXPECTED_FIELDS = {"prompt_id", "prompt", "story_text", "language", "model_name", "seed", "generation_type"}
MODEL_FAMILY = {
    "alijawad07/aya-23-8B-AWQ-GEMM": ("aya", "reserved"),
    "AMead10/c4ai-command-r-08-2024-awq": ("command-r", "reserved"),
    "AMead10/SuperNova-Medius-AWQ": ("qwen2.5", "reserved"),
    "arcee-ai/Arcee-Blitz-AWQ": ("mistral", "development"),
    "casperhansen/mistral-nemo-instruct-2407-awq": ("mistral", "development"),
    "harborwater/Gemma-2-9B-It-SPPO-Iter3-AWQ": ("gemma2", "development"),
    "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4": ("llama3.1", "development"),
    "Orion-zhen/aya-expanse-32b-AWQ": ("aya", "reserved"),
    "Orion-zhen/aya-expanse-8b-AWQ": ("aya", "reserved"),
    "Qwen/Qwen2.5-14B-Instruct-AWQ": ("qwen2.5", "reserved"),
    "solidrust/gemma-2-9b-it-AWQ": ("gemma2", "development"),
    "solidrust/Gemma-2-Ataraxy-9B-AWQ": ("gemma2", "development"),
    "solidrust/Hermes-3-Llama-3.1-8B-AWQ": ("llama3.1", "development"),
    "stelterlab/Mistral-Small-24B-Instruct-2501-AWQ": ("mistral", "development"),
    "stelterlab/phi-4-AWQ": ("phi4", "reserved"),
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _download(path: Path, url: str, expected_sha: str) -> bytes:
    if path.exists():
        raw = path.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "textector-narrative-validation/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
        if sha256(raw) != expected_sha:
            raise ValueError("la descarga no coincide con el SHA-256 fijado")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    if sha256(raw) != expected_sha:
        raise ValueError(f"hash incorrecto en caché: {path}")
    return raw


def preparar(source: Path | None = None, out: Path = CORPUS) -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    ai = protocol["ai_source"]
    cache = out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    source = source or cache / ai["file"]
    raw = _download(source, ai["url"], ai["sha256"])
    if sha256(raw) != ai["sha256"]:
        raise ValueError("el CSV local no coincide con la revisión fijada")

    development: list[dict] = []
    reserved: list[dict] = []
    seen_ids: set[str] = set()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if not EXPECTED_FIELDS <= fields:
            raise ValueError("faltan columnas requeridas: " + ", ".join(sorted(EXPECTED_FIELDS - fields)))
        for row in reader:
            if row["language"].strip().lower() != "es":
                continue
            model = row["model_name"].strip()
            if model not in MODEL_FAMILY:
                raise ValueError("modelo sin asignación de familia: " + model)
            family, split = MODEL_FAMILY[model]
            text = row["story_text"].strip()
            prompt_id = row["prompt_id"].strip()
            if not text or not prompt_id:
                raise ValueError("registro español sin texto o prompt_id")
            text_hash = sha256(text.encode("utf-8"))
            identity = f"{model}|{prompt_id}|{row['seed']}|{row['generation_type']}|{text_hash}"
            case_id = "ai-" + sha256(identity.encode("utf-8"))[:20]
            if case_id in seen_ids:
                raise ValueError("id duplicado modelo/prompt: " + identity)
            seen_ids.add(case_id)
            folder = "development" if split == "development" else "reserved"
            rel = f"{folder}/texts/{case_id}.txt"
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            text_raw = (text + "\n").encode("utf-8")
            target.write_bytes(text_raw)
            record = {
                "id": case_id,
                "label": "ai",
                "panel": "narrative_ai_" + split,
                "group": family,
                "author_or_model": model,
                "prompt_id": prompt_id,
                "source_id": "story_writing_benchmark:" + prompt_id,
                "prompt_sha256": sha256(row["prompt"].strip().encode("utf-8")),
                "generation_type": row["generation_type"],
                "seed": row["seed"],
                "path": rel,
                "sha256": sha256(text_raw),
                "source_revision": ai["revision"],
            }
            (development if split == "development" else reserved).append(record)

    manifest_hashes = {}
    for split, rows in (("development", development), ("reserved", reserved)):
        path = out / split / "manifest-ai.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.sort(key=lambda item: item["id"])
        manifest_raw = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")
        path.write_bytes(manifest_raw)
        manifest_hashes[split] = sha256(manifest_raw)

    prompts_dev = {row["prompt_id"] for row in development}
    prompts_holdout = {row["prompt_id"] for row in reserved}
    result = {
        "source_sha256": sha256(raw),
        "n_spanish": len(development) + len(reserved),
        "development": len(development),
        "reserved": len(reserved),
        "models_development": sorted({row["author_or_model"] for row in development}),
        "models_reserved": sorted({row["author_or_model"] for row in reserved}),
        "shared_prompt_ids": len(prompts_dev & prompts_holdout),
        "human_panel_ready": False,
        "scores_computed": False,
        "manifest_sha256": manifest_hashes,
    }
    lock = {
        "id": "narrative-v1-ai-selection",
        "created_utc": "2026-10-25T00:00:00Z",
        "source_revision": ai["revision"],
        "source_file_sha256": sha256(raw),
        "manifests_sha256": manifest_hashes,
        "selection": "language == es; all source rows; split only by predeclared base family; no quality/score/prediction filtering",
        "counts": {"spanish": len(development) + len(reserved), "development": len(development), "reserved": len(reserved)},
        "models_development": result["models_development"],
        "models_reserved": result["models_reserved"],
        "shared_prompt_ids": result["shared_prompt_ids"],
        "scores_computed": False,
    }
    (out / "ai-selection-lock.json").write_text(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "preparation-summary.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="CSV local ya descargado; si se omite usa cache/average.csv")
    parser.add_argument("--out", type=Path, default=CORPUS)
    args = parser.parse_args(argv)
    result = preparar(args.source, args.out.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
