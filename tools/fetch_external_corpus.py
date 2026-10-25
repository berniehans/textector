"""Restaura los textos del manifiesto externo desde versiones públicas fijadas.

Descarga datos solamente; no ejecuta scripts del proveedor ni genera texto IA.
Las licencias de cada fuente se conservan en el manifiesto y LICENSES.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(text):
    return text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def _download(url, path, expected, prefix_bytes=None):
    if path.exists():
        raw = path.read_bytes()
    else:
        headers = {"User-Agent": "textector-research/0.3.1"}
        if prefix_bytes:
            headers["Range"] = f"bytes=0-{prefix_bytes - 1}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
            raw = response.read(prefix_bytes) if prefix_bytes else response.read()
        if _sha(raw) != expected:
            raise ValueError("la descarga no coincide con la versión fijada")
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(raw)
    if _sha(raw) != expected:
        raise ValueError("hash incorrecto en caché: " + path.name)
    return raw


def _prefix_records(raw, count=1000):
    text = raw.decode("utf-8", errors="ignore")
    decoder = json.JSONDecoder()
    pos, records = 1, []
    while len(records) < count:
        while pos < len(text) and text[pos] in " \n\r\t,":
            pos += 1
        record, pos = decoder.raw_decode(text, pos)
        records.append(record)
    return records


def restaurar(corpus_dir: Path, cache_dir: Path):
    protocol = json.loads((corpus_dir / "protocol.json").read_text(encoding="utf-8"))
    sources = json.loads((corpus_dir / "sources.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (corpus_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    books = {}
    for book in sources["books"]:
        raw = _download(book["url"], cache_dir / (book["book_id"] + ".txt"), book["raw_sha256"])
        books[book["book_id"]] = _canonical(raw.decode(book["encoding"]))
    tiny = sources["tiny"]
    raw = _download(tiny["url"], cache_dir / "tiny-stories_01.prefix",
                    protocol["source_shards"]["tiny-stories_01.prefix"], tiny["limit_bytes"])
    tiny_rows = _prefix_records(raw)
    iber_rows = [row for row in rows if row["panel"] == "iber_literary_es"]
    raw = _download(iber_rows[0]["url"], cache_dir / "iberautextification-train.tsv",
                    protocol["source_shards"]["iberautextification-train.tsv"])
    wanted = {row["source_id"] for row in iber_rows}
    iber = {r["id"]: r["text"] for r in csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t") if r["id"] in wanted}
    for row in rows:
        if row["panel"] == "libros_pre2020":
            text = books[row["book_id"]][row["canonical_source_start"]:row["canonical_source_end"]]
        elif row["panel"] == "tiny_es":
            text = _canonical(tiny_rows[row["source_row_index"]]["story"])
        else:
            text = _canonical(iber[row["source_id"]])
        raw = text.encode("utf-8")
        if _sha(raw) != row["sha256"]:
            raise ValueError("no se pudo reproducir el texto: " + row["id"])
        target = (corpus_dir / row["path"]).resolve()
        if not target.is_relative_to(corpus_dir.resolve()):
            raise ValueError("ruta fuera del corpus")
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_bytes(raw)
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "validation/external-v1")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args(argv)
    count = restaurar(args.corpus, args.cache_dir or args.corpus / "cache")
    print(f"{count} textos restaurados con SHA256 verificado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
