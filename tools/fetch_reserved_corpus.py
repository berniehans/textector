"""Restaura los textos reservados desde snapshots públicos fijados y verifica hashes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(text: str) -> str:
    return text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def _download(url: str, path: Path, expected: str, prefix_bytes: int | None = None) -> bytes:
    if path.exists():
        raw = path.read_bytes()
    else:
        headers = {"User-Agent": "textector-research/0.3.0"}
        if prefix_bytes:
            headers["Range"] = f"bytes=0-{prefix_bytes - 1}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read(prefix_bytes) if prefix_bytes else response.read()
        if _sha(raw) != expected:
            raise ValueError("descarga no coincide con el snapshot congelado")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    if _sha(raw) != expected:
        raise ValueError("hash incorrecto en caché: " + path.name)
    return raw


def _prefix_records(raw: bytes, count: int = 1000) -> list[dict]:
    text = raw.decode("utf-8", errors="ignore")
    decoder = json.JSONDecoder()
    pos, records = 1, []
    while len(records) < count:
        while pos < len(text) and text[pos] in " \n\r\t,":
            pos += 1
        record, pos = decoder.raw_decode(text, pos)
        records.append(record)
    return records


def restaurar(corpus: Path, cache: Path) -> int:
    manifest_raw = (corpus / "manifest.jsonl").read_bytes()
    sources = json.loads((corpus / "sources.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in manifest_raw.decode("utf-8").splitlines()]
    lock = json.loads((corpus / "selection-lock.json").read_text(encoding="utf-8"))
    if _sha(manifest_raw) != lock["manifest_sha256"]:
        raise ValueError("el manifiesto no coincide con el candado de selección")

    books: dict[str, str] = {}
    for book in sources["books"]:
        raw = _download(book["url"], cache / (book["book_id"] + ".txt"), book["raw_sha256"])
        books[book["book_id"]] = _canonical(raw.decode(book["encoding"]))

    tiny_meta = sources["tiny"]
    tiny_raw = _download(tiny_meta["url"], cache / "stories_02.prefix",
                         tiny_meta["prefix_sha256"], tiny_meta["prefix_bytes"])
    tiny = _prefix_records(tiny_raw)

    iber_meta = sources["iber"]
    iber_raw = _download(iber_meta["url"], cache / "iberautextification-train.tsv",
                         iber_meta["raw_sha256"])
    wanted = {row["source_id"] for row in rows if row["panel"] == "iber_nuevos_prompts"}
    iber = {item["id"]: item["text"] for item in csv.DictReader(
        io.StringIO(iber_raw.decode("utf-8")), delimiter="\t") if item["id"] in wanted}

    for row in rows:
        if row["panel"] == "humanos_autores_nuevos":
            book = books[row["book_id"]]
            text = book[row["canonical_start"]:row["canonical_end"]]
        elif row["panel"] == "tiny_nuevo_shard":
            text = _canonical(tiny[row["source_row_index"]]["story"])
        else:
            text = _canonical(iber[row["source_id"]])
        raw = text.encode("utf-8")
        if _sha(raw) != row["sha256"]:
            raise ValueError("no se pudo reproducir el texto: " + row["id"])
        target = (corpus / row["path"]).resolve()
        if not target.is_relative_to(corpus.resolve()):
            raise ValueError("ruta fuera del corpus")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    if len(rows) != lock["n"]:
        raise ValueError("el manifiesto y el candado de selección discrepan")
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path,
                        default=Path(__file__).resolve().parents[1] / "validation/reserved-f5-v1")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args(argv)
    n = restaurar(args.corpus.resolve(), (args.cache_dir or args.corpus / "cache").resolve())
    print(f"{n} textos restaurados con SHA256 verificado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
