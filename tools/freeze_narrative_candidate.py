"""Congela F5 y las fuentes de comparación antes de abrir la reserva narrativa."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.validate_narrative_corpus import validate

CORPUS = ROOT / "validation/narrative-v1"
PREVIOUS_LOCK = ROOT / "validation/reserved-f5-v1/candidate-lock.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def freeze() -> dict:
    if (CORPUS / "results.json").exists():
        raise ValueError("la reserva narrativa ya tiene resultados; no se vuelve a congelar")
    validation = validate(CORPUS)
    previous = json.loads(PREVIOUS_LOCK.read_text(encoding="utf-8"))
    detector_sources = previous["detector_sources"]
    for name, expected in detector_sources.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != expected:
            raise ValueError("el detector F5 no coincide con el candidato previamente congelado: " + name)
    protocol_raw = (CORPUS / "protocol.json").read_bytes()
    f4_protocol_raw = (ROOT / "validation/external-v1/protocol.json").read_bytes()
    selection_raw = (CORPUS / "selection-lock.json").read_bytes()
    manifest_raw = (CORPUS / "reserved/manifest.jsonl").read_bytes()
    protocol = json.loads(protocol_raw)
    candidate = {
        "id": "narrative-v1-candidate-lock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen-before-reserved-scoring",
        "method": "f5-portable-v1",
        "threshold": json.loads((ROOT / "config/f5-portable.json").read_text(encoding="utf-8"))["threshold"],
        "f5_detector_sources": detector_sources,
        "selection_and_evaluator_sources": {
            name: sha((ROOT / name).read_bytes()) for name in (
                "tools/prepare_narrative_corpus.py",
                "tools/prepare_gutenberg_narrative.py",
                "tools/validate_narrative_corpus.py",
                "tools/compare_narrative_v1.py",
            )
        },
        "f4_baseline_root": previous["f4_baseline_root"],
        "f4_external_protocol_sha256": sha(f4_protocol_raw),
        "f4_previous_lock_protocol_reference": previous["f4_original_protocol_sha256"],
        "f4_previous_lock_protocol_reference_present": sha(f4_protocol_raw) == previous["f4_original_protocol_sha256"],
        "protocol_sha256": sha(protocol_raw),
        "selection_lock_sha256": sha(selection_raw),
        "reserved_manifest_sha256": sha(manifest_raw),
        "development_manifest_sha256": sha((CORPUS / "development/manifest.jsonl").read_bytes()),
        "promotion_gates": protocol["promotion_gates"],
        "no_parameter_changes_after_evaluation": True,
        "reserved_set_read": False,
        "validation_summary": validation,
    }
    lock_path = CORPUS / "candidate-lock.json"
    lock_path.write_text(json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return candidate


if __name__ == "__main__":
    print(json.dumps(freeze(), ensure_ascii=False, indent=2))
