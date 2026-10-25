"""Evalúa un corpus externo congelado sin entrenar ni ajustar parámetros."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cli import _cargar_lexicon, _cargar_semillas
from tools.decision import MARGEN, UMBRAL, prediccion
from tools.pipeline import puntuar
from tools.resources import CONFIG
from tools.scoring import VERSION_METODO


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def resumir(casos):
    conteo = Counter()
    insuficientes = Counter()
    for c in casos:
        clase, pred = c["label"], c["predicho"]
        conteo["n"] += 1
        conteo["n_ia" if clase == "ia" else "n_humanos"] += 1
        if pred == "abstencion":
            conteo["abstenciones_ia" if clase == "ia" else "abstenciones_humano"] += 1
            conteo["abstencion_insuficiencia" if c["indice_llm"] is None else "abstencion_banda"] += 1
        else:
            clave = ("tp" if pred == "ia" else "fn") if clase == "ia" else ("fp" if pred == "ia" else "tn")
            conteo[clave] += 1
        insuficientes.update(c["checks_insuficientes"])
    m = {k: conteo[k] for k in ("n", "n_ia", "n_humanos", "tp", "tn", "fp", "fn",
                               "abstenciones_ia", "abstenciones_humano",
                               "abstencion_insuficiencia", "abstencion_banda")}
    def ratio(a, b):
        return a / b if b else None
    ni, nh = m["tp"] + m["fn"], m["tn"] + m["fp"]
    valores = [c["indice_llm"] for c in casos if c["indice_llm"] is not None]
    return {"conteos": m, "metricas": {
        "cobertura_decision": ratio(ni + nh, m["n"]),
        "cobertura_score": ratio(len(valores), m["n"]),
        "cobertura_ia": ratio(ni, m["n_ia"]),
        "cobertura_humano": ratio(nh, m["n_humanos"]),
        "sensibilidad_condicionada": ratio(m["tp"], ni),
        "especificidad_condicionada": ratio(m["tn"], nh),
        "tasa_fp_condicionada": ratio(m["fp"], nh),
        "detecciones_ia_sobre_total_ia": ratio(m["tp"], m["n_ia"]),
        "falsos_positivos_sobre_total_humanos": ratio(m["fp"], m["n_humanos"]),
    }, "scores": {"n": len(valores), "min": min(valores) if valores else None,
                  "mediana": statistics.median(valores) if valores else None,
                  "max": max(valores) if valores else None},
        "checks_insuficientes": dict(sorted(insuficientes.items()))}


def bootstrap_especificidad(casos):
    """Intervalo descriptivo por autor; no supone fragmentos independientes."""
    grupos = defaultdict(list)
    for caso in casos:
        if caso["label"] == "human":
            grupos[caso["group"]].append(caso)
    rng = random.Random(20261025)
    nombres = sorted(grupos)
    if len(nombres) < 2:
        return None
    valores = []
    for _ in range(2000):
        muestra = [c for nombre in rng.choices(nombres, k=len(nombres)) for c in grupos[nombre]]
        valor = resumir(muestra)["metricas"]["especificidad_condicionada"]
        if valor is not None:
            valores.append(valor)
    valores.sort()
    return {"unidad": "autor/obra", "clusters": len(nombres), "repeticiones": 2000,
            "intervalo_percentil_95": [valores[int(.025 * (len(valores)-1))], valores[int(.975 * (len(valores)-1))]] if valores else None,
            "aviso": "Descriptivo; nueve autores no representan toda la prosa humana."}


def evaluar(corpus_dir: Path):
    protocolo_raw = (corpus_dir / "protocol.json").read_bytes()
    protocolo = json.loads(protocolo_raw)
    if protocolo["method"] != VERSION_METODO or (protocolo["umbral"], protocolo["margen"]) != (UMBRAL, MARGEN):
        raise ValueError("el método o los umbrales cambiaron después de congelar el corpus")
    for relative, expected in protocolo["frozen_detector"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or _sha(path.read_bytes()) != expected:
            raise ValueError("cambió una fuente congelada del detector: " + relative)
    manifest_raw = (corpus_dir / "manifest.jsonl").read_bytes()
    sources = json.loads((corpus_dir / "sources.json").read_bytes())
    if sources["protocol_sha256"] != _sha(protocolo_raw):
        raise ValueError("protocolo no coincide con la selección")
    rows = [json.loads(line) for line in manifest_raw.decode("utf-8").splitlines()]
    ids = set()
    lexicon, semillas = _cargar_lexicon(CONFIG), _cargar_semillas()
    casos = []
    for row in rows:
        if row["id"] in ids or row["label"] not in {"human", "ia"}:
            raise ValueError("id duplicado o etiqueta inválida")
        ids.add(row["id"])
        path = (corpus_dir / row["path"]).resolve()
        if not path.is_relative_to(corpus_dir.resolve()):
            raise ValueError("ruta fuera del corpus")
        raw = path.read_bytes()
        if _sha(raw) != row["sha256"]:
            raise ValueError("hash de texto no coincide: " + row["id"])
        if row["label"] == "human" and row["source_date"] >= "2020-01-01":
            raise ValueError("texto humano sin evidencia anterior a 2020")
        informe = puntuar(raw.decode("utf-8"), lexicon, semillas)
        score = informe["indice_llm"]
        casos.append({**{k: row[k] for k in ("id", "label", "panel", "group", "author_or_model", "sha256", "tokens", "paragraphs")},
                      "indice_llm": score, "predicho": prediccion(score),
                      "n_disponibles": informe["n_disponibles"],
                      "checks_insuficientes": sorted(set(("burstiness", "mattr", "uniformity", "cliches_es", "compression")) - set(informe["resultado"]))})
    paneles = {p: resumir([c for c in casos if c["panel"] == p]) for p in sorted({c["panel"] for c in casos})}
    principal = [c for c in casos if c["panel"] in {"libros_pre2020", "tiny_es"}]
    grupos = {g: resumir([c for c in casos if c["group"] == g]) for g in sorted({c["group"] for c in casos})}
    return {"corpus": protocolo["id"], "version": VERSION_METODO,
            "evaluated_utc": datetime.now(timezone.utc).isoformat(), "umbral": UMBRAL, "margen": MARGEN,
            "protocol_sha256": _sha(protocolo_raw), "manifest_sha256": _sha(manifest_raw),
            "evaluator_sha256": _sha(Path(__file__).read_bytes()), "seleccion": "congelada antes de puntuar",
            "integridad_textos": f"{len(rows)}/{len(rows)} hashes correctos",
            "panel_principal": resumir(principal), "paneles": paneles, "grupos": grupos,
            "bootstrap_humano": bootstrap_especificidad(casos), "casos": casos,
            "limitaciones": protocolo["limitations"],
            "uso_futuro": "Este corpus ya se ha evaluado: pasa a benchmark consumido; no es un holdout virgen para ajustar y volver a validar.",
            "generacion_nueva": False, "parametros_modificados": False,
            "holdout_anterior": "sin evaluar"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "validation/external-v1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = evaluar(args.corpus)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
