"""Metadata-only-output preflight for Spanish fiction in a pinned WildChat release.

The script streams one parquet shard at a time. It never prints or writes any
prompt, response, or raw conversation ID. Only counts and SHA-256 fingerprints
are retained. Raw shards are deleted after each shard has been processed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "validation/narrative-v2-corpus-audit"
REVISION = "475fa490b5e28692362af7a6ec66810caf4a9847"
REPO = "allenai/WildChat"
MODELS = {"gpt-3.5-turbo", "gpt-4", "gpt-4-1106-preview"}
MIN_TOKENS = 50
MAX_TOKENS = 2500

NARRATIVE_REQUEST = re.compile(
    r"\b(?:escrib(?:e|eme|a|ame)|redact(?:a|ame)|cre(?:a|ame)|inventa|cu[eé]ntame|"
    r"narra|relata|imagina|contin[uú]a|desarrolla|genera|comp[oó]n)\b.{0,160}\b"
    r"(?:cuento|historia|relato|narraci[oó]n|novela|ficci[oó]n|f[aá]bula|leyenda|escena)\b",
    re.IGNORECASE | re.DOTALL,
)
NARRATIVE_NOUN = re.compile(
    r"\b(?:un|una|el|la|este|esta)\s+(?:cuento|historia|relato|narraci[oó]n|"
    r"novela|ficci[oó]n|f[aá]bula|leyenda)\b",
    re.IGNORECASE,
)
PERSONAL_OR_REAL_WORLD = re.compile(
    r"\b(?:mi|mis|m[ií]o|m[ií]a|me|yo|nosotros|nuestra familia|mi familia|"
    r"mi pareja|mi hijo|mi hija|mi amigo|mi amiga|mi trabajo|mi experiencia|"
    r"mi problema|mi historia real|basado en hechos reales|persona real|"
    r"figura p[uú]blica|pol[ií]tico actual)\b",
    re.IGNORECASE,
)
SENSITIVE_CONTENT = re.compile(
    r"\b(?:porn(?:o|ogr[aá]fic[oa])?|er[oó]tic[oa]|sexo expl[ií]cito|"
    r"violaci[oó]n|abuso sexual|menor de edad|autolesi[oó]n|suicidi[oa]|"
    r"gore|tortura expl[ií]cita)\b",
    re.IGNORECASE,
)
PII_PATTERN = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://\S+|www\.\S+|"
    r"\b(?:dni|ruc|pasaporte|tel[eé]fono|m[oó]vil|direcci[oó]n)\b\s*[:#-]?\s*[\w.+()/-]{4,}|"
    r"\+?\d[\d .()/-]{7,}\d|\b(?:calle|av\.?|avenida|jr\.?|jiron|pasaje)\s+[^,.;]{0,80}\d+)",
    re.IGNORECASE,
)
MODEL_DISCLOSURE = re.compile(r"\b(?:como modelo de lenguaje|soy una inteligencia artificial|no puedo escribir)\b", re.I)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_key(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def token_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, re.UNICODE))


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?…]+(?:[\"'»)]*)\s+|[.!?…]+$", text.strip()))


def spanish(language: object) -> bool:
    return str(language).strip().casefold() in {"spanish", "es", "spa"}


def get_messages(row: dict) -> tuple[str, str] | None:
    messages = row.get("conversation") or []
    if len(messages) != 2:
        return None
    if [m.get("role") for m in messages] != ["user", "assistant"]:
        return None
    if any(m.get("redacted") or m.get("toxic") for m in messages):
        return None
    if not all(spanish(m.get("language")) for m in messages):
        return None
    return str(messages[0].get("content") or ""), str(messages[1].get("content") or "")


def process_parquet(path: Path, counts: Counter, eligible: dict[str, dict], prompt_fingerprints: dict[str, set[str]]) -> int:
    rows_seen = 0
    parquet = pq.ParquetFile(path)
    columns = ["conversation_id", "model", "conversation", "turn", "language", "toxic", "redacted"]
    for batch in parquet.iter_batches(batch_size=128, columns=columns):
        for row in batch.to_pylist():
            rows_seen += 1
            model = row.get("model")
            if model not in MODELS:
                continue
            c = counts[model]
            c["model_rows"] += 1
            if not spanish(row.get("language")):
                continue
            c["spanish_rows"] += 1
            if row.get("redacted"):
                c["row_redacted"] += 1
                continue
            if row.get("toxic"):
                c["row_toxic"] += 1
                continue
            if row.get("turn") != 1:
                c["not_single_turn"] += 1
                continue
            messages = get_messages(row)
            if messages is None:
                c["message_structure_or_language_excluded"] += 1
                continue
            prompt, response = messages
            if not prompt.strip() or not response.strip():
                c["empty_prompt_or_response"] += 1
                continue
            # Apply privacy and sensitive-content exclusions before any narrative
            # heuristic. Text is examined in memory only and never logged.
            if PII_PATTERN.search(prompt) or PII_PATTERN.search(response):
                c["pii_pattern_excluded"] += 1
                continue
            if PERSONAL_OR_REAL_WORLD.search(prompt):
                c["personal_or_real_world_prompt_excluded"] += 1
                continue
            if SENSITIVE_CONTENT.search(prompt) or SENSITIVE_CONTENT.search(response):
                c["sensitive_content_excluded"] += 1
                continue
            if MODEL_DISCLOSURE.search(response):
                c["model_disclaimer_excluded"] += 1
                continue
            c["privacy_screen_pass"] += 1
            if not (NARRATIVE_REQUEST.search(prompt) or NARRATIVE_NOUN.search(prompt)):
                c["not_explicit_fiction_request"] += 1
                continue
            c["explicit_fiction_request"] += 1
            tokens = token_count(response)
            if not MIN_TOKENS <= tokens <= MAX_TOKENS or sentence_count(response) < 3:
                c["response_not_eligible_length_or_sentence_count"] += 1
                continue
            # Deduplicate exact normalized prompts; don't retain the prompt or
            # response itself. Conversation IDs are stored only as hashes.
            prompt_hash = sha(clean_key(prompt))
            if prompt_hash in prompt_fingerprints[model]:
                c["duplicate_normalized_prompt"] += 1
                continue
            prompt_fingerprints[model].add(prompt_hash)
            conversation_hash = sha(str(row.get("conversation_id") or ""))
            response_hash = sha(response)
            eligible[model][conversation_hash] = {
                "conversation_id_sha256": conversation_hash,
                "prompt_sha256": prompt_hash,
                "response_sha256": response_hash,
                "tokens": tokens,
                "sentences": sentence_count(response),
            }
            c["unique_candidate_prompts"] += 1
    return rows_seen


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="textector-wildchat-", dir=AUDIT))
    try:
        req = urllib.request.Request(
            "https://huggingface.co/api/datasets/allenai/WildChat/tree/" + REVISION + "/data?recursive=true",
            headers={"User-Agent": "textector-public-corpus-preflight/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            files = json.load(response)
        shards = [item for item in files if item.get("path", "").endswith(".parquet")]
        if len(shards) != 6:
            raise RuntimeError(f"pinned source expected 6 parquet shards; found {len(shards)}")

        counts: dict[str, Counter] = defaultdict(Counter)
        eligible = {model: {} for model in MODELS}
        prompt_fingerprints = {model: set() for model in MODELS}
        shard_hashes = {}
        total_rows = 0
        for index, item in enumerate(shards, start=1):
            relative = item["path"]
            url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{relative}"
            path = tmp / Path(relative).name
            h = hashlib.sha256()
            downloaded = 0
            request = urllib.request.Request(url, headers={"User-Agent": "textector-public-corpus-preflight/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response, path.open("wb") as target:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    target.write(block)
                    h.update(block)
                    downloaded += len(block)
            if downloaded != item.get("size"):
                raise RuntimeError(f"download size mismatch for pinned shard {relative}")
            shard_hashes[relative] = h.hexdigest()
            rows = process_parquet(path, counts, eligible, prompt_fingerprints)
            total_rows += rows
            path.unlink()
            print(f"processed metadata shard {index}/6; rows={rows}; bytes={downloaded}", flush=True)

        # Sort by hashed conversation ID for stable manifest and aggregate hashes.
        models = {}
        for model in sorted(MODELS):
            records = sorted(eligible[model].values(), key=lambda r: r["conversation_id_sha256"])
            aggregate = hashlib.sha256("\n".join(
                f"{r['conversation_id_sha256']}:{r['prompt_sha256']}:{r['response_sha256']}" for r in records
            ).encode()).hexdigest()
            models[model] = {
                "counts": dict(counts[model]),
                "unique_candidate_prompt_count": len(records),
                "candidate_fingerprint_sha256": aggregate,
                "privacy_review_status": "automated preflight only; candidate set is not approved for scoring",
            }
        result = {
            "id": "wildchat-spanish-fiction-preflight-v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source": REPO,
            "revision": REVISION,
            "license": "ODC-BY",
            "method": "metadata and safe-text heuristic preflight; no F5 scoring",
            "privacy": {
                "raw_prompts_or_responses_written": False,
                "raw_conversation_ids_written": False,
                "filters": [
                    "row not redacted and not toxic",
                    "one user/assistant exchange only",
                    "both utterances detected as Spanish and neither utterance redacted/toxic",
                    "exclude PII-pattern matches, personal/real-world requests, sensitive content, and model disclaimers",
                ],
                "limitation": "Regex filters cannot guarantee removal of all sensitive personal information; this output is only a size/provenance preflight.",
            },
            "unit": "one conversation with one exact-normalized unique Spanish fiction prompt; user-level independence is unavailable",
            "threshold_for_next_gate": {"minimum_unique_prompts_per_model": 150},
            "total_rows_scanned": total_rows,
            "shard_sha256": shard_hashes,
            "models": models,
        }
        out = AUDIT / "wildchat-spanish-fiction-preflight.json"
        out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "summary_path": str(out.relative_to(ROOT)),
            "total_rows_scanned": total_rows,
            "candidate_counts": {model: models[model]["unique_candidate_prompt_count"] for model in sorted(MODELS)},
            "no_raw_text_written": True,
        }, ensure_ascii=False, indent=2))
    finally:
        for child in tmp.iterdir():
            child.unlink()
        tmp.rmdir()


if __name__ == "__main__":
    main()
