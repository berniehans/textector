"""Fija fragmentos narrativos humanos pre-2020 de snapshots de Project Gutenberg."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "validation/narrative-v1"
SOURCES = CORPUS / "human-source-candidates.json"
TARGET_WORDS = [484, 550, 650, 730, 730, 800, 1000, 1186]
GAP_WORDS = 250
CUTOFF = datetime(2020, 1, 1)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(raw: bytes) -> tuple[str, str]:
    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    except UnicodeDecodeError as exc:
        raise ValueError("la fuente no es UTF-8; se requiere una codificación revisada manualmente") from exc
    return text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n"), encoding


def metadata(text: str, expected: dict) -> tuple[datetime, str]:
    fields = {}
    for key in ("Title", "Author", "Language", "Release date"):
        match = re.search(rf"(?im)^{re.escape(key)}:\s*(.+)$", text)
        if not match:
            raise ValueError(f"falta {key} en Project Gutenberg #{expected['id']}")
        fields[key] = match.group(1).strip()
    date_text = fields["Release date"].split(" [eBook", 1)[0]
    release_date = datetime.strptime(date_text, "%B %d, %Y")
    if release_date >= CUTOFF:
        raise ValueError(f"fuente digital posterior al corte: #{expected['id']} {date_text}")
    if fields["Language"].strip().lower() != "spanish":
        raise ValueError(f"idioma no exclusivamente español: #{expected['id']} {fields['Language']}")
    if fields["Author"].casefold() != expected["author"].casefold():
        raise ValueError(f"autor distinto en #{expected['id']}: {fields['Author']}")
    if fields["Title"].casefold() != expected["title"].casefold():
        raise ValueError(f"título distinto en #{expected['id']}: {fields['Title']}")
    return release_date, fields["Language"]


def _download(source: dict, path: Path) -> bytes:
    if path.exists():
        raw = path.read_bytes()
    else:
        request = urllib.request.Request(source["url"], headers={"User-Agent": "textector-narrative-validation/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
        if sha256(raw) != source["sha256"]:
            raise ValueError(f"la descarga no coincide con el hash fijado: #{source['id']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    if sha256(raw) != source["sha256"]:
        raise ValueError(f"hash incorrecto en caché: #{source['id']}")
    return raw


def _body(text: str, book_id: int) -> str:
    start = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.I | re.S)
    end = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.I | re.S)
    if not start or not end or end.start() <= start.end():
        raise ValueError(f"no se reconocieron los límites Gutenberg del libro #{book_id}")
    body = text[start.end():end.start()].strip()
    if "\ufffd" in body or re.search(r"(?i)<\s*(?:html|body|p|div)\b", body):
        raise ValueError(f"texto con señal de corrupción/HTML en #{book_id}")
    return body


def _sample(body: str, targets: list[int], gap: int, book_id: int) -> list[tuple[str, int, int, int]]:
    words = list(re.finditer(r"\S+", body))
    need = sum(targets) + gap * (len(targets) - 1)
    free = len(words) - need
    if free < 0:
        raise ValueError(f"libro #{book_id} demasiado corto para {len(targets)} fragmentos emparejados")
    result = []
    cursor = 0
    margin = round(free / (len(targets) + 1))
    for index, count in enumerate(targets):
        start_word = cursor + margin
        end_word = start_word + count
        start_char, end_char = words[start_word].start(), words[end_word - 1].end()
        excerpt = body[start_char:end_char].strip()
        actual_words = len(re.findall(r"\S+", excerpt))
        if actual_words != count:
            raise ValueError(f"falló el tamaño determinista en #{book_id}")
        result.append((excerpt, start_char, end_char, actual_words))
        cursor = end_word + gap
    return result


def preparar(source_list: Path = SOURCES, out: Path = CORPUS) -> dict:
    books = json.loads(source_list.read_text(encoding="utf-8-sig"))
    if len(books) != 30 or len({item["author"] for item in books}) != 30:
        raise ValueError("se requieren 30 libros de 30 autores distintos")
    splits = {name: [item for item in books if item["split"] == name]
              for name in ("development", "reserved")}
    if any(len(rows) != 15 for rows in splits.values()):
        raise ValueError("cada split debe contener 15 autores")
    used_authors: set[str] = set()
    manifests: dict[str, list[dict]] = {"development": [], "reserved": []}
    raw_hashes = {}
    cache = out / "cache/human-source"
    for source in books:
        author = source["author"]
        if author in used_authors:
            raise ValueError("autor duplicado entre splits: " + author)
        used_authors.add(author)
        raw = _download(source, cache / f"pg{source['id']}.txt")
        normalized, encoding = canonical(raw)
        release_date, language = metadata(normalized, source)
        body = _body(normalized, source["id"])
        excerpts = _sample(body, TARGET_WORDS, GAP_WORDS, source["id"])
        for number, (excerpt, start, end, n_words) in enumerate(excerpts, 1):
            split = source["split"]
            case_id = f"human-{source['id']}-{number:02d}"
            rel = f"{split}/texts/{case_id}.txt"
            text_raw = (excerpt + "\n").encode("utf-8")
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text_raw)
            manifests[split].append({
                "id": case_id,
                "label": "human",
                "panel": "narrative_human_" + split,
                "group": str(source["id"]),
                "author_or_model": author,
                "book_id": str(source["id"]),
                "title": source["title"],
                "genre": source.get("genre", "narrative"),
                "source_date": release_date.date().isoformat(),
                "source_url": f"https://www.gutenberg.org/ebooks/{source['id']}",
                "source_raw_sha256": source["sha256"],
                "source_encoding": encoding,
                "canonical_start": start,
                "canonical_end": end,
                "n_words": n_words,
                "path": rel,
                "sha256": sha256(text_raw),
            })
        raw_hashes[str(source["id"])] = source["sha256"]

    hashes = {}
    for split, rows in manifests.items():
        rows.sort(key=lambda row: row["id"])
        raw = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")
        (out / split).mkdir(parents=True, exist_ok=True)
        (out / split / "manifest-human.jsonl").write_bytes(raw)
        hashes[split] = sha256(raw)

    lock = {
        "id": "narrative-v1-human-selection",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_register_sha256": sha256(source_list.read_bytes()),
        "source_raw_sha256": dict(sorted(raw_hashes.items())),
        "manifest_sha256": hashes,
        "selection": {
            "books": "15 libros de 15 autores sin repetición por split; decisión fijada antes de puntuar",
            "per_book_fragments": len(TARGET_WORDS),
            "target_words_per_fragment": TARGET_WORDS,
            "gap_words": GAP_WORDS,
            "method": "ventanas no solapadas distribuidas uniformemente dentro del texto entre marcadores Gutenberg; sin filtrado por score, cobertura o predicción",
        },
        "counts": {split: len(rows) for split, rows in manifests.items()},
        "no_scores_computed": True,
    }
    (out / "human-selection-lock.json").write_text(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    ai_lock_path = out / "ai-selection-lock.json"
    if ai_lock_path.exists():
        ai_lock = json.loads(ai_lock_path.read_text(encoding="utf-8"))
        combined_hashes = {}
        for split in ("development", "reserved"):
            human_rows = [json.loads(line) for line in (out / split / "manifest-human.jsonl").read_text(encoding="utf-8").splitlines()]
            ai_rows = [json.loads(line) for line in (out / split / "manifest-ai.jsonl").read_text(encoding="utf-8").splitlines()]
            combined = sorted(human_rows + ai_rows, key=lambda row: row["id"])
            combined_raw = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in combined).encode("utf-8")
            (out / split / "manifest.jsonl").write_bytes(combined_raw)
            combined_hashes[split] = sha256(combined_raw)
        total_lock = {
            "id": "narrative-v1-selection",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": sha256((out / "protocol.json").read_bytes()),
            "ai_selection_lock_sha256": sha256(ai_lock_path.read_bytes()),
            "human_selection_lock_sha256": sha256((out / "human-selection-lock.json").read_bytes()),
            "development_manifest_sha256": combined_hashes["development"],
            "reserved_manifest_sha256": combined_hashes["reserved"],
            "counts": {
                "development": {"human": lock["counts"]["development"], "ai": ai_lock["counts"]["development"]},
                "reserved": {"human": lock["counts"]["reserved"], "ai": ai_lock["counts"]["reserved"]},
            },
            "holdout_scores_computed": False,
        }
        (out / "selection-lock.json").write_text(json.dumps(total_lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"authors_development": len(splits["development"]), "authors_reserved": len(splits["reserved"]),
            "fragments_development": len(manifests["development"]), "fragments_reserved": len(manifests["reserved"]),
            "manifest_sha256": hashes, "scores_computed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-list", type=Path, default=SOURCES)
    parser.add_argument("--out", type=Path, default=CORPUS)
    args = parser.parse_args(argv)
    print(json.dumps(preparar(args.source_list, args.out.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
