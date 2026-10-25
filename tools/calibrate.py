"""Calibración F3 de textector: split por grupos, barrido de umbral y holdout.

Lee el corpus congelado (``corpus/manifest.csv`` + textos), puntúa cada
texto con el pipeline F2 CONGELADO (los 5 checks + ``scoring.compute_indice``;
NO retoca pesos ni transformaciones: ver docs/methodology.md) y ajusta el
UMBRAL del índice con elección honesta:

- Split por GRUPOS (unidad = autor/obra humano; prompt/pieza IA), no por
  comando bidón: HOLDOUT = {h03, h04, h08, a05, a09}; el resto TRAIN.
- Elección del umbral SOLO con TRAIN: barrido determinista de
  (umbral, margen de abstención) + validación cruzada leave-one-group-out
  dentro de TRAIN (los grupos del holdout nunca participan).
- El HOLDOUT se abre UNA VEZ (``main()`` imprime el reporte final): matriz
  TP/FP/TN/FN, tasa de FPs sobre humanos y lista de abstenciones. Los
  tests NO abren el holdout (solo split/seeds/manifest/determinismo).

Semillas de compresión: ``corpus/seeds/seed_ia_es.txt`` y
``corpus/seeds/seed_hum_es.txt`` son concatenaciones EXACTAS (unidas por
``\\n\\n``) de los textos de TRAIN de su clase. El holdout NO aporta
semillas. Nota honesta: el check ``compression`` está congelado en F2 con
fixtures sintéticas; estas semillas ES reales quedan construidas y
verificadas por checksum para el wiring posterior (sin retazar el check).

Determinista, stdlib, sin red. Reporte JSON con claves ordenadas.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

__all__ = [
    "GRUPO_HUMANO", "GRUPO_IA", "HOLDOUT", "AREA_UMBRAL", "MARGENES",
    "cargar_corpus", "puntuar", "split_grupos", "evaluar_holdout", "main",
]

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.csv"

# Grupos por AUTOR/OBRA humano y PROMPT/PIEZA IA (una pieza por grupo).
HOLDOUT: frozenset[str] = frozenset({"h03", "h04", "h08", "a05", "a09"})
GRUPO_HUMANO = "humano"
GRUPO_IA = "ia"

# Barrido determinista del umbral y del margen de abstención.
AREA_UMBRAL = range(0, 101)  # umbar candidato (índice entero 0..100)
MARGENES: tuple[int, ...] = (0, 2, 4, 6, 8)


# ---------------------------------------------------------------------------
# Carga del corpus y puntuación (pipeline F2 congelado)
# ---------------------------------------------------------------------------

def cargar_corpus() -> dict[str, dict[str, str]]:
    """Lee el manifest y devuelve id -> fila dict (con texto desde disco)."""
    if not MANIFEST.exists():
        raise FileNotFoundError(f"manifest no encontrado: {MANIFEST}")
    filas: dict[str, dict[str, str]] = {}
    with MANIFEST.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = (row.get("id") or "").strip()
            if not pid:
                continue
            sub = "human" if pid.startswith("h") else "llm"
            path = CORPUS / sub / f"{pid}.txt"
            fila = {k: (v or "").strip() for k, v in row.items()}
            fila["texto"] = path.read_text(encoding="utf-8")
            filas[pid] = fila
    if len(filas) != 20:
        raise ValueError(f"manifest con {len(filas)} filas; se esperaban 20")
    return filas


def puntuar(texto: str) -> dict[str, Any]:
    """Pipeline F2 congelado: los 5 checks + compute_indice (sin I/O extra)."""
    from tools.checks import burstiness, cliches_es, compression, mattr, uniformity
    from tools.scoring import compute_indice

    resultados = {
        "burstiness": burstiness.check(texto),
        "mattr": mattr.check(texto),
        "uniformity": uniformity.check(texto),
        "cliches_es": cliches_es.check(texto),
        "compression": compression.check(texto),
    }
    return compute_indice(resultados)


def _indice_de(texto: str) -> int | None:
    """Índice entero del pipeline congelado; None si texto insuficiente."""
    informe = puntuar(texto)
    return informe["indice_llm"]


def split_grupos(corpus: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    """Divide ids en train/holdout por GRUPO. Determinista y exacta."""
    train: list[str] = []
    holdout: list[str] = []
    for pid in sorted(corpus):
        if pid in HOLDOUT:
            holdout.append(pid)
        else:
            train.append(pid)
    return {"train": train, "holdout": holdout}


# ---------------------------------------------------------------------------
# Predicción con abstención (banda centrada en el umbral)
# ---------------------------------------------------------------------------

def _prediccion(idx: int | None, umbral: int, margen: int) -> str:
    if idx is None:
        return "abstencion"
    if abs(idx - umbral) <= margen:
        return "abstencion"
    return GRUPO_IA if idx > umbral else GRUPO_HUMANO


def _tasas(ids, corpus, umbral, margen, idx_de, esperado) -> tuple[float, float]:
    tp = tn = fp = fn = 0
    for pid in ids:
        pred = _prediccion(idx_de.get(pid), umbral, margen)
        if pred == "abstencion":
            continue
        if esperado[pid] == GRUPO_IA:
            if pred == GRUPO_IA:
                tp += 1
            else:
                fn += 1
        else:
            if pred == GRUPO_IA:
                fp += 1
            else:
                tn += 1
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    return tpr, tnr


def _barrido_train(
    corpus: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Elección del umbral y margen con SOLO train + CV por grupos."""
    train = split_grupos(corpus)["train"]
    idx_de = {pid: _indice_de(corpus[pid]["texto"]) for pid in train}
    esperado = {pid: (GRUPO_HUMANO if pid.startswith("h") else GRUPO_IA) for pid in train}

    # Grupos: cada id es su grupo (autor/obra humano; prompt IA).
    grupos: dict[str, list[str]] = {}
    for pid in train:
        grupos.setdefault(pid, []).append(pid)

    # CV leave-one-group-out: umbral/margen del fold se elige con el resto.
    folded: list[dict[str, Any]] = []
    for pid_sal in sorted(grupos):
        calib = [p for p in train if p not in grupos[pid_sal]]
        test = grupos[pid_sal]
        mejor = _elegir(calib, idx_de, esperado)
        tpr, tnr = _tasas(test, corpus, mejor["umbral"], mejor["margen"], idx_de, esperado)
        folded.append(
            {"grupo": pid_sal, "umbral": mejor["umbral"], "margen": mejor["margen"],
             "tpr_fold": round(tpr, 4), "tnr_fold": round(tnr, 4)}
        )
    a_tpr = [f["tpr_fold"] for f in folded]
    a_tnr = [f["tnr_fold"] for f in folded]
    cv = {
        "folds": folded,
        "cv_tpr_media": round(sum(a_tpr) / len(a_tpr), 4),
        "cv_tnr_media": round(sum(a_tnr) / len(a_tnr), 4),
    }

    # Umbral/margen FINAL: sweep sobre TODO el train (elegir solo con train).
    final = _elegir(train, idx_de, esperado)
    barrido = []
    for umbral in AREA_UMBRAL:
        for margen in MARGENES:
            tpr, tnr = _tasas(train, corpus, umbral, margen, idx_de, esperado)
            barrido.append(
                {"umbral": umbral, "margen": margen, "tpr": round(tpr, 4),
                 "tnr": round(tnr, 4), "balanced": round((tpr + tnr) / 2, 4)}
            )
    return {"cv": cv, "final": final, "barrido": barrido, "idx_train": idx_de}


def _elegir(ids, idx_de, esperado) -> dict[str, int | float]:
    """Pares (umbral, margen) de train; máximo balanced; desempate determinista."""
    mejor: dict[str, int | float] | None = None
    for umbral in AREA_UMBRAL:
        for margen in MARGENES:
            tpr, tnr = _tasas(ids, None, umbral, margen, idx_de, esperado)
            cand = {
                "bal": (tpr + tnr) / 2, "tpr": tpr, "tnr": tnr,
                "umbral": umbral, "margen": margen,
            }
            if mejor is None or _mejor(cand, mejor):
                mejor = cand
    return mejor


def _mejor(a, b) -> bool:
    """True si ``a`` > ``b``: max bal; luego clama menos abst NL; luego menor |u-50|."""
    if a["bal"] != b["bal"]:
        return a["bal"] > b["bal"]
    if a["margen"] != b["margen"]:
        return a["margen"] < b["margen"]
    return abs(a["umbral"] - 50) < abs(b["umbral"] - 50)


# ---------------------------------------------------------------------------
# Holdout (UNA apertura por escriptorio: main() la ejecuta al final)
# ---------------------------------------------------------------------------

def evaluar_holdout(corpus: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Matriz TP/FP/TN/FN del HOLDOUT con (umbral, margen) de TRAIN.

    Llámala UNA VEZ por proceso (``main()``): reporte honesto con los casos
    que falla. Los tests NO la invocan.
    """
    umbral = _UMBRAL_ELEGIDO["umbral"]
    margen = int(_UMBRAL_ELEGIDO["margen"])
    holdout = split_grupos(corpus)["holdout"]
    tp = tn = fp = fn = ab = 0
    casos: list[dict[str, Any]] = []
    for pid in holdout:
        idx = _indice_de(corpus[pid]["texto"])
        pred = _prediccion(idx, umbral, margen)
        esperado = GRUPO_HUMANO if pid.startswith("h") else GRUPO_IA
        if pred == "abstencion":
            ab += 1
        elif esperado == GRUPO_IA:
            if pred == GRUPO_IA:
                tp += 1
            else:
                fn += 1
        elif pred == GRUPO_IA:
            fp += 1
        else:
            tn += 1
        casos.append(
            {"id": pid, "indice": idx, "predicho": pred, "esperado": esperado}
        )
    humanos = [c for c in casos if c["esperado"] == GRUPO_HUMANO and c["predicho"] != "abstencion"]
    tasa_fp = (fp / len(humanos)) if humanos else None
    return {
        "umbral": umbral,
        "margen": margen,
        "matriz": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "tasa_fp_humanos": None if tasa_fp is None else round(tasa_fp, 4),
        "abstenciones": ab,
        "casos": casos,
    }


_UMBRAL_ELEGIDO: dict[str, int | float] = {"umbral": 0, "margen": 0}


def main() -> int:
    """Ejecución completa: barrido+CV en train, luego holdout UNA VEZ."""
    global _UMBRAL_ELEGIDO
    corpus = cargar_corpus()
    reporte: dict[str, Any] = {}
    b = _barrido_train(corpus)
    _UMBRAL_ELEGIDO = {
        "umbral": int(b["final"]["umbral"]),
        "margen": int(b["final"]["margen"]),
    }
    reporte["train"] = {
        "cv": b["cv"],
        "eleccion": b["final"],
        "indices": b["idx_train"],
    }
    reporte["holdout"] = evaluar_holdout(corpus)
    print(json.dumps(reporte, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
