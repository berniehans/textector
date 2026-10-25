"""Crosswalk public novel-catalog metadata against known human exposure.

This script reads metadata only. Its input list is intentionally explicit and
does not include either reserved-corpus directory or any text files.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "validation/narrative-v2-corpus-audit/source-metadata"
GUTENBERG_META = ROOT.parent / "corpus-scout/gutendex-es-all.json"
OUT = ROOT / "validation/narrative-v2-corpus-audit/human-author-crosswalk.json"
EXPECTED_HASHES = {
    "conssa-metadata.tsv": "2c127dbb6f82b33548151e09a5a185a384c36981eb14e7fd1c7cfab54f035400",
    "eltec-spa-metadata.tsv": "ffcee033007c2a239f3046ee71ef089687e398ee6103a27a11ad22b6931fb3cb",
    "conha19-metadata-free.csv": "e38f930cdbbf07686bbd6c49df1790894f97d464530ac41109570488bd8086d2",
    "conha19-metadata-all.csv": "975d4dcae3c2721caf5b572b77a4144b80d5215de871b77a83a79ef8b59e8ebc",
}
GUTENBERG_SHA256 = "1a77aef20110ab5188f3c561c25712ccf12680b6a3dc7a4fc10676b4524f005a"

# Canonicalize known forms that cannot be resolved by accents and punctuation.
ALIASES = {
    "leopoldo alas clarin": "leopoldo alas",
    "clarin": "leopoldo alas",
    "fernán caballero": "fernan caballero",
    "cecilia bohl de faber": "fernan caballero",
    "cecilia bohl de faber y ruiz de larrea": "fernan caballero",
    "bohl de faber y ruiz de larrea cecilia fernan caballero": "fernan caballero",
    "jacinto octavio picon": "jacinto octavio picon",
    "j o picon": "jacinto octavio picon",
    "j o picon jacinto octavio picon": "jacinto octavio picon",
    "j m de pereda": "jose maria de pereda",
    "jose maria de pereda": "jose maria de pereda",
    "p a de alarcon": "pedro antonio de alarcon",
    "pedro antonio de alarcon": "pedro antonio de alarcon",
    "manuel fernandez y gonzalez": "manuel fernandez y gonzalez",
    "fernandez y gonzalez manuel": "manuel fernandez y gonzalez",
    "azorin jose martinez ruiz": "azorin jose martinez ruiz",
    "jose martinez ruiz azorin": "azorin jose martinez ruiz",
    "azorin": "azorin jose martinez ruiz",
    "emilia condesa de pardo bazan": "emilia pardo bazan",
    "miguel de cervantes saavedra": "miguel de cervantes",
    "bunge carlos o carlos octavio": "carlos o bunge",
    "juan ramon jimenez": "juan ramon jimenez",
    "jimenez juan ramon": "juan ramon jimenez",
}

DOCUMENTED_PRIOR_RESERVED_AUTHORS = [
    "Concha Espina",
    "Armando Palacio Valdés",
    "Rafael Delgado",
    "Felipe Trigo",
]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\[[^]]*\]", " ", value)
    if "," in value:
        surname, given = value.split(",", 1)
        value = f"{given} {surname}"
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).lower()
    value = " ".join(value.split())
    return ALIASES.get(value, value)


def read_prior_exposure() -> set[str]:
    authors: set[str] = set(DOCUMENTED_PRIOR_RESERVED_AUTHORS)
    with (ROOT / "corpus/manifest.csv").open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("clase", "").lower() in {"human", "humano"}:
                authors.add(row.get("autor_o_modelo", ""))
    for relative in (
        "validation/narrative-v1/development/manifest-human.jsonl",
        "validation/external-v1/manifest.jsonl",
    ):
        with (ROOT / relative).open(encoding="utf-8") as file:
            for line in file:
                row = json.loads(line)
                author = row.get("author_or_model", "")
                is_human = relative.endswith("manifest-human.jsonl") or row.get("label", "").lower() in {
                    "human", "humano"
                }
                if is_human and author:
                    authors.add(author)
    return {normalize(author) for author in authors if author.strip()}


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"snapshot SHA-256 mismatch: {path.name}")


def main() -> None:
    for filename, digest in EXPECTED_HASHES.items():
        verify_sha256(META / filename, digest)
    verify_sha256(GUTENBERG_META, GUTENBERG_SHA256)
    prior = read_prior_exposure()
    conssa_rows = list(csv.DictReader((META / "conssa-metadata.tsv").open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    eltec_rows = list(csv.DictReader((META / "eltec-spa-metadata.tsv").open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    conha_rows = list(csv.DictReader((META / "conha19-metadata-free.csv").open(encoding="utf-8-sig", newline="")))
    gutenberg_rows = json.loads(GUTENBERG_META.read_text(encoding="utf-8"))

    conssa_authors = sorted({row["author.name.full"].strip() for row in conssa_rows
                             if row.get("availability") == "free" and row.get("author.name.full", "").strip()})
    eltec_authors = sorted({row["author-name"].strip() for row in eltec_rows if row.get("author-name", "").strip()})
    conha_author_keys = sorted({row["author-short"].strip() for row in conha_rows if row.get("author-short", "").strip()})

    gutenberg_authors: set[str] = set()
    gutenberg_narrative_authors: set[str] = set()
    for book in gutenberg_rows:
        tags = " ".join(book.get("subjects", []) + book.get("bookshelves", [])).lower()
        is_narrative = "fiction" in tags or any(term in tags for term in ("novel", "short stor", "tales", "drama"))
        for author in book.get("authors", []):
            name = author.get("name", "").strip()
            if not name:
                continue
            key = normalize(name)
            gutenberg_authors.add(name)
            if is_narrative:
                gutenberg_narrative_authors.add(name)

    def report(names: list[str]) -> dict:
        seen, new = [], []
        for name in names:
            item = {"name": name, "canonical": normalize(name)}
            (seen if item["canonical"] in prior else new).append(item)
        return {"total_identities_raw": len(names), "prior_exposure": seen, "not_exactly_crossmatched": new}

    candidate_names = {
        "CoNSSA_free": conssa_authors,
        "ELTeC-spa": eltec_authors,
        "Gutendex_narrative_tags": sorted(gutenberg_narrative_authors),
    }
    candidate_norms = {
        source: {normalize(name) for name in names if normalize(name) not in prior}
        for source, names in candidate_names.items()
    }
    cross_source_overlap = {}
    for left, right in (("CoNSSA_free", "ELTeC-spa"), ("CoNSSA_free", "Gutendex_narrative_tags"), ("ELTeC-spa", "Gutendex_narrative_tags")):
        cross_source_overlap[f"{left}__{right}"] = sorted(candidate_norms[left] & candidate_norms[right])

    result = {
        "scope": "metadata-only; no text contents read or scored",
        "prior_exposure_canonical_count": len(prior),
        "candidate_new_identity_union_count_before_manual_review": len(set.union(*candidate_norms.values())),
        "candidate_cross_source_identity_overlap": cross_source_overlap,
        "prior_reserved_authors_from_nonreserved_documentation": DOCUMENTED_PRIOR_RESERVED_AUTHORS,
        "sources": {
            "CoNSSA_free": {
                "revision": "8fccf669ed1bdbad309ff190f5afb0d6066d70a3",
                "catalog_rows": len(conssa_rows),
                "free_rows": sum(row.get("availability") == "free" for row in conssa_rows),
                **report(conssa_authors),
            },
            "ELTeC-spa": {
                "revision": "83e2a22d5ef66f96e59f47f7ef810358c4236322",
                "catalog_rows": len(eltec_rows),
                **report(eltec_authors),
            },
            "Conha19_free_metadata_only": {
                "revision": "d5def0a3b5900fd37172714d1b8b91bfce0a267c",
                "free_rows": len(conha_rows),
                "author_short_keys": conha_author_keys,
                "identity_resolution": "unresolved; do not count as new authors until matched to full bibliographic names and text-level rights are verified",
            },
            "Gutendex_Spanish_catalog_snapshot": {
                "snapshot_file": "../../../corpus-scout/gutendex-es-all.json",
                "snapshot_sha256": GUTENBERG_SHA256,
                "catalog_rows": len(gutenberg_rows),
                **report(sorted(gutenberg_authors)),
                "narrative_tagged_author_count_raw": len(gutenberg_narrative_authors),
                "narrative_tagged_not_exactly_crossmatched": [name for name in sorted(gutenberg_narrative_authors) if normalize(name) not in prior],
                "caveat": "Gutendex category/subject tags are a candidate filter, not human genre verification; author names, translation rights, publication dates, and per-book source snapshots need review.",
            },
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "prior_author_identities": len(prior),
        "CoNSSA": {"records": len(conssa_rows), "free_authors": len(conssa_authors), "known_exposure": len(result["sources"]["CoNSSA_free"]["prior_exposure"])},
        "ELTeC-spa": {"records": len(eltec_rows), "authors": len(eltec_authors), "known_exposure": len(result["sources"]["ELTeC-spa"]["prior_exposure"])},
        "Conha19": {"free_records": len(conha_rows), "author_keys_unresolved": len(conha_author_keys)},
        "Gutendex": {"catalog_rows": len(gutenberg_rows), "narrative_authors_raw": len(gutenberg_narrative_authors), "narrative_authors_unmatched": sum(normalize(name) not in prior for name in gutenberg_narrative_authors)},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
