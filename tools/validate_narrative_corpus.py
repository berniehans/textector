"""Comprueba integridad y separación del corpus narrativo, sin puntuar detectores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "validation/narrative-v1"
OLD_HUMAN_AUTHORS = [
    "Miguel de Cervantes", "Anonymous", "Francisco de Quevedo", "Ricardo Palma",
    "Emilia Pardo Bazán", "Benito Pérez Galdós", "Juan Valera", "Leopoldo Alas",
    "Gustavo Adolfo Bécquer", "Mariano José de Larra", "Miguel de Unamuno",
    "Horacio Quiroga", "Pío Baroja", "Vicente Blasco Ibáñez", "Ramón del Valle-Inclán",
    "Rubén Darío", "José Martí", "Enrique Larreta", "Juan Ramón Jiménez", "Concha Espina",
    "Armando Palacio Valdés", "Rafael Delgado", "Felipe Trigo",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text.casefold(), flags=re.UNICODE)


def previous_text_paths() -> list[Path]:
    paths = list((ROOT / "corpus/seeds").glob("*.txt"))
    for corpus_name in ("external-v1", "reserved-f5-v1"):
        corpus = ROOT / "validation" / corpus_name
        manifest = corpus / "manifest.jsonl"
        if not manifest.exists():
            continue
        rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
        paths.extend(corpus / row["path"] for row in rows if (corpus / row["path"]).exists())
    return paths


def validate(corpus: Path = CORPUS, check_overlap: bool = True) -> dict:
    protocol = json.loads((corpus / "protocol.json").read_text(encoding="utf-8"))
    selection = json.loads((corpus / "selection-lock.json").read_text(encoding="utf-8"))
    ai_lock_path, human_lock_path = corpus / "ai-selection-lock.json", corpus / "human-selection-lock.json"
    ai_lock, human_lock = json.loads(ai_lock_path.read_text(encoding="utf-8")), json.loads(human_lock_path.read_text(encoding="utf-8"))
    if selection["protocol_sha256"] != sha((corpus / "protocol.json").read_bytes()):
        raise ValueError("el protocolo cambió después de fijar la selección")
    if selection["ai_selection_lock_sha256"] != sha(ai_lock_path.read_bytes()):
        raise ValueError("el lock IA no coincide con la selección total")
    if selection["human_selection_lock_sha256"] != sha(human_lock_path.read_bytes()):
        raise ValueError("el lock humano no coincide con la selección total")

    split_rows: dict[str, list[dict]] = {}
    file_count = 0
    for split in ("development", "reserved"):
        manifest_raw = (corpus / split / "manifest.jsonl").read_bytes()
        expected = selection["development_manifest_sha256" if split == "development" else "reserved_manifest_sha256"]
        if sha(manifest_raw) != expected:
            raise ValueError("hash de manifiesto incorrecto: " + split)
        rows = [json.loads(line) for line in manifest_raw.decode("utf-8").splitlines()]
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError("ids duplicados en " + split)
        for row in rows:
            path = (corpus / row["path"]).resolve()
            if not path.is_relative_to(corpus.resolve()):
                raise ValueError("ruta fuera del corpus: " + row["id"])
            raw = path.read_bytes()
            if sha(raw) != row["sha256"]:
                raise ValueError("hash de texto incorrecto: " + row["id"])
            text = raw.decode("utf-8")
            if not text.strip() or "\ufffd" in text:
                raise ValueError("texto vacío o con reemplazo de caracteres: " + row["id"])
            if row["label"] == "human":
                if row["source_date"] >= "2020-01-01":
                    raise ValueError("fecha humana no anterior a 2020: " + row["id"])
                if not 200 <= row["n_words"] <= 1500:
                    raise ValueError("longitud humana fuera de rango: " + row["id"])
                if len(words(text)) < 200:
                    raise ValueError("conteo de palabras inconsistente: " + row["id"])
            elif row["label"] != "ai":
                raise ValueError("etiqueta no reconocida: " + row["id"])
            file_count += 1
        split_rows[split] = rows

    dev, holdout = split_rows["development"], split_rows["reserved"]
    dev_human = [row for row in dev if row["label"] == "human"]
    holdout_human = [row for row in holdout if row["label"] == "human"]
    dev_ai = [row for row in dev if row["label"] == "ai"]
    holdout_ai = [row for row in holdout if row["label"] == "ai"]
    dev_authors = {norm(row["author_or_model"]) for row in dev_human}
    holdout_authors = {norm(row["author_or_model"]) for row in holdout_human}
    known = [norm(author) for author in OLD_HUMAN_AUTHORS]
    overlaps = sorted({row["author_or_model"] for row in dev_human + holdout_human
                       if any(name in norm(row["author_or_model"]) or norm(row["author_or_model"]) in name for name in known)})
    if overlaps:
        raise ValueError("autores ya usados en corpus previos: " + ", ".join(overlaps))
    if dev_authors & holdout_authors:
        raise ValueError("hay autores compartidos entre desarrollo y reserva")
    if len(dev_authors) < 15 or len(holdout_authors) < 15:
        raise ValueError("no se alcanzan 15 autores por split")

    model_development = {row["author_or_model"] for row in dev_ai}
    model_reserved = {row["author_or_model"] for row in holdout_ai}
    if model_development & model_reserved:
        raise ValueError("hay checkpoints IA compartidos entre splits")
    for source_rows in (dev_ai, holdout_ai):
        per_model = {}
        for row in source_rows:
            per_model[row["author_or_model"]] = per_model.get(row["author_or_model"], 0) + 1
        if not per_model or any(count != 224 for count in per_model.values()):
            raise ValueError("un checkpoint IA no tiene 224 ejemplos")

    overlap_count = None
    if check_overlap:
        prior_shingles: set[tuple[str, ...]] = set()
        for path in previous_text_paths():
            tokens = words(path.read_text(encoding="utf-8"))
            prior_shingles.update(tuple(tokens[i:i + 20]) for i in range(max(0, len(tokens) - 19)))
        new_human = dev_human + holdout_human
        found = []
        for row in new_human:
            tokens = words((corpus / row["path"]).read_text(encoding="utf-8"))
            if any(tuple(tokens[i:i + 20]) in prior_shingles for i in range(max(0, len(tokens) - 19))):
                found.append(row["id"])
        overlap_count = len(found)
        if found:
            raise ValueError("solapamiento de 20 palabras con fuentes anteriores: " + ", ".join(found[:10]))

    return {
        "protocol": protocol["id"],
        "development": {"n": len(dev), "human": len(dev_human), "human_authors": len(dev_authors),
                        "ai": len(dev_ai), "checkpoints": len(model_development)},
        "reserved": {"n": len(holdout), "human": len(holdout_human), "human_authors": len(holdout_authors),
                     "ai": len(holdout_ai), "checkpoints": len(model_reserved)},
        "source_files_hash_verified": file_count,
        "known_author_overlap": overlaps,
        "prior_20_word_overlap_human": overlap_count,
        "prompt_ids_shared_across_ai_splits": ai_lock["shared_prompt_ids"],
        "ai_selection_lock_sha256": sha(ai_lock_path.read_bytes()),
        "human_selection_lock_sha256": sha(human_lock_path.read_bytes()),
        "scores_computed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--skip-overlap", action="store_true", help="omitir comparación de 20 palabras con corpus anteriores")
    args = parser.parse_args(argv)
    print(json.dumps(validate(args.corpus.resolve(), not args.skip_overlap), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
