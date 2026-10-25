"""Evaluación TRAIN con semillas por fold y tasas agregadas fuera de muestra.

El holdout histórico se conserva cerrado por defecto. Los resultados de f4
no validan autoría ni sustituyen un corpus y holdout nuevos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.decision import prediccion as _prediccion
from tools.pipeline import puntuar as puntuar_pipeline
from tools.resources import CONFIG, SEED_IA, SEED_HUM
from tools.scoring import VERSION_METODO

CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.csv"
SEED_MANIFEST = CORPUS / "seeds" / "manifest.json"
_SEMILLAS_REALES = None
_LEXICON_COMPLETO = None

# Holdout v2: FIJO (elegido de una sola vez; no cambia después).
HOLDOUT_V2: frozenset[str] = frozenset({"h08", "h16", "h19", "a05", "a07", "b03"})
# Alias de compatibilidad: mismo conjunto v2.
HOLDOUT: frozenset[str] = HOLDOUT_V2

GRUPO_HUMANO = "humano"
GRUPO_IA = "ia"

# Grupos por AUTOR humano (la unidad de CV es el autor, no el archivo).
GRUPOS_HUMANO: dict[str, str] = {
    "h01": "cervantes",
    "h02": "anonimo_lazarillo",
    "h03": "quevedo",
    "h04": "palma",
    "h05": "pardo_bazan",
    "h06": "galdos",
    "h07": "valera",
    "h08": "alas_clarin",
    "h09": "becquer",
    "h10": "larra",
    "h11": "p_a_alarcon",      # pg15532
    "h12": "fernan_caballero",
    "h13": "coloma",
    "h14": "pereda",           # h14 y h17 comparten grupo (mismo autor)
    "h15": "picon",
    "h16": "alas_clarin",
    "h17": "pereda",
    "h18": "j_ruiz_de_alarcon",
    "h19": "zorrilla",
    "h20": "escosura",
}

# Subtipos humanos del informe: clásicos = Siglos de Oro (XVI-XVII):
# h01 Cervantes, h02 Lazarillo, h03 Quevedo, h18 J. Ruiz de Alarcón.
# Modernos = restantes (XVIII-XIX). Constante explícita, sin deducciones.
CLASICOS: frozenset[str] = frozenset({"h01", "h02", "h03", "h18"})

# Barrido determinista del umbral y del margen de abstención.
AREA_UMBRAL = range(0, 101)  # umbar candidato (índice entero 0..100)
MARGENES: tuple[int, ...] = (0, 2, 4, 6, 8)



def _subcarpeta(pid: str) -> str:
    for prefix, folder in (("h", "human"), ("a", "llm"), ("b", "news")):
        if pid.startswith(prefix):
            return folder
    raise ValueError("id de corpus desconocido")


def _dominio_ia(pid: str) -> str:
    return {"h": "literatura_pd", "a": "narrativa_propia", "b": "noticias_sinteticas"}.get(pid[:1], "")


def _grupo_de(pid: str) -> str:
    if pid.startswith("h"):
        return GRUPOS_HUMANO[pid]
    return pid if pid.startswith("a") else "zenodo"


def cargar_corpus() -> dict[str, dict[str, str]]:
    filas = {}
    esperados = {f"h{i:02}" for i in range(1, 21)} | {f"{p}{i:02}" for p in "ab" for i in range(1, 11)}
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = row["id"].strip()
            if pid not in esperados:
                raise ValueError("id desconocido en manifest")
            if pid in filas:
                raise ValueError("id duplicado en manifest")
            path = CORPUS / _subcarpeta(pid) / (pid + ".txt")
            raw = path.read_bytes()
            texto = raw.decode("utf-8")
            if hashlib.sha256(raw).hexdigest() != row["SHA256"]:
                raise ValueError(f"SHA256 no coincide: {pid}")
            if len(texto) != int(row["chars"]):
                raise ValueError(f"longitud no coincide: {pid}")
            clase = "human" if pid.startswith("h") else "llm"
            if row["clase"] != clase or not row["licencia"].strip():
                raise ValueError(f"metadatos inválidos: {pid}")
            filas[pid] = {**row, "texto": texto, "dominio": _dominio_ia(pid)}
    if set(filas) != esperados:
        raise ValueError("manifest no contiene los 40 ids esperados")
    return filas


def _semillas_reales() -> tuple[str, str]:
    global _SEMILLAS_REALES
    if _SEMILLAS_REALES is None:
        from tools.cli import _cargar_semillas
        _SEMILLAS_REALES = _cargar_semillas(SEED_IA, SEED_HUM)
    return _SEMILLAS_REALES


def _lexicon_completo():
    global _LEXICON_COMPLETO
    if _LEXICON_COMPLETO is None:
        from tools.cli import _cargar_lexicon
        _LEXICON_COMPLETO = _cargar_lexicon(CONFIG)
    return _LEXICON_COMPLETO


def puntuar(texto: str, semillas: tuple[str, str] | None = None) -> dict[str, Any]:
    return puntuar_pipeline(texto, _lexicon_completo(), semillas if semillas is not None else _semillas_reales())


def _indice_de(texto: str, semillas=None) -> int | None:
    return puntuar(texto, semillas)["indice_llm"]


def split_grupos(corpus) -> dict[str, list[str]]:
    # Split histórico fijo por ids. Zenodo cruza TRAIN/holdout: límite declarado.
    return {"train": sorted(set(corpus) - HOLDOUT_V2),
            "holdout": sorted(set(corpus) & HOLDOUT_V2)}


def _semillas_para(corpus, ids):
    """Subconjunto histórico documentado, limitado a los ids del fold TRAIN."""
    receta = json.loads(SEED_MANIFEST.read_text(encoding="utf-8"))
    permitidos = set(ids)
    if permitidos & HOLDOUT_V2:
        raise ValueError("el holdout no puede aportar semillas")
    textos, miembros = [], {}
    for clase in ("ia", "humana"):
        elegidos = [pid for pid in receta[clase]["ids"] if pid in permitidos]
        if not elegidos:
            raise ValueError("fold sin fuentes suficientes para ambas semillas")
        textos.append("\n\n".join(corpus[pid]["texto"] for pid in elegidos))
        miembros[clase] = elegidos
    return tuple(textos), miembros


def _matriz(ids, idx_de, esperado, umbral, margen):
    m = dict(tp=0, tn=0, fp=0, fn=0, abstenciones_ia=0, abstenciones_humano=0)
    for pid in ids:
        pred = _prediccion(idx_de[pid], umbral, margen)
        ia = esperado[pid] == GRUPO_IA
        if pred == "abstencion":
            clave = "abstenciones_ia" if ia else "abstenciones_humano"
        elif ia:
            clave = "tp" if pred == GRUPO_IA else "fn"
        else:
            clave = "fp" if pred == GRUPO_IA else "tn"
        m[clave] += 1
    return m


def _metricas(m):
    ni = m["tp"] + m["fn"]
    nh = m["tn"] + m["fp"]
    total = ni + nh + m["abstenciones_ia"] + m["abstenciones_humano"]
    tpr = m["tp"] / ni if ni else None
    tnr = m["tn"] / nh if nh else None
    return {"tpr": tpr, "tnr": tnr,
            "balanced": (tpr + tnr) / 2 if tpr is not None and tnr is not None else None,
            "cobertura": (ni + nh) / total if total else 0.0,
            "cobertura_ia": ni / (ni + m["abstenciones_ia"]) if ni + m["abstenciones_ia"] else None,
            "cobertura_humano": nh / (nh + m["abstenciones_humano"]) if nh + m["abstenciones_humano"] else None}


def _tasas(ids, corpus, umbral, margen, idx_de, esperado):
    m = _metricas(_matriz(ids, idx_de, esperado, umbral, margen))
    return m["tpr"], m["tnr"]


def _mejor(a, b):
    def orden(c):
        return (c["bal"], c["cobertura"], -c["margen"], -abs(c["umbral"] - 50))
    return orden(a) > orden(b)


def _elegir(ids, idx_de, esperado):
    mejor = None
    for umbral in AREA_UMBRAL:
        for margen in MARGENES:
            met = _metricas(_matriz(ids, idx_de, esperado, umbral, margen))
            if met["balanced"] is None:
                continue
            cand = {"bal": met["balanced"], "tpr": met["tpr"], "tnr": met["tnr"],
                    "cobertura": met["cobertura"], "umbral": umbral, "margen": margen}
            if mejor is None or _mejor(cand, mejor):
                mejor = cand
    if mejor is None:
        raise ValueError("no hay casos evaluables de ambas clases para elegir umbral")
    return mejor


def _barrido_train(corpus):
    train = split_grupos(corpus)["train"]
    esperado = {p: GRUPO_HUMANO if p.startswith("h") else GRUPO_IA for p in train}
    grupos = {}
    for pid in train:
        grupos.setdefault(_grupo_de(pid), []).append(pid)
    folds, predicciones = [], []
    total = dict(tp=0, tn=0, fp=0, fn=0, abstenciones_ia=0, abstenciones_humano=0)
    for grupo, test in sorted(grupos.items()):
        calib = [p for p in train if p not in test]
        semillas, fuentes = _semillas_para(corpus, calib)
        # Recalcular AMBOS lados con las semillas de ese fold; nunca puntuar test
        # con el texto propio o de su grupo dentro de una semilla.
        indices = {p: _indice_de(corpus[p]["texto"], semillas) for p in train}
        mejor = _elegir(calib, indices, esperado)
        m = _matriz(test, indices, esperado, mejor["umbral"], mejor["margen"])
        for k in total:
            total[k] += m[k]
        folds.append({"grupo": grupo, "piezas": test, "fuentes_semillas": fuentes,
                      "sha256_semillas": [hashlib.sha256(t.encode()).hexdigest() for t in semillas],
                      "umbral": mejor["umbral"], "margen": mejor["margen"],
                      "matriz": m, "metricas": _metricas(m)})
        predicciones.extend({"id": p, "indice": indices[p], "esperado": esperado[p],
                             "predicho": _prediccion(indices[p], mejor["umbral"], mejor["margen"])} for p in test)
    semillas, fuentes = _semillas_para(corpus, train)
    indices = {p: _indice_de(corpus[p]["texto"], semillas) for p in train}
    return {"version": VERSION_METODO, "cv": {"folds": folds, "matriz": total,
            "metricas": _metricas(total), "predicciones": predicciones},
            "final": _elegir(train, indices, esperado), "idx_train": indices,
            "fuentes_semillas": fuentes,
            "aviso": "Evaluación interna exploratoria; requiere corpus y holdout nuevos. "
                     "La elección final no actualiza la referencia provisional del CLI."}


def evaluar_holdout(corpus, *, umbral=None, margen=None):
    if umbral is None or margen is None:
        raise ValueError("se exige umbral y margen explícitos antes de abrir el holdout")
    ids = split_grupos(corpus)["holdout"]
    semillas, _ = _semillas_para(corpus, split_grupos(corpus)["train"])
    indices = {p: _indice_de(corpus[p]["texto"], semillas) for p in ids}
    esperado = {p: GRUPO_HUMANO if p.startswith("h") else GRUPO_IA for p in ids}
    matriz = _matriz(ids, indices, esperado, umbral, margen)
    return {"umbral": umbral, "margen": margen, "matriz": matriz,
            "metricas": _metricas(matriz), "indices": indices,
            "aviso": "Holdout histórico consumido: esta ejecución no aporta validación nueva."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluar-holdout", action="store_true",
                        help="reproducción explícita del holdout histórico ya consumido")
    args = parser.parse_args(argv)
    corpus = cargar_corpus()
    train = _barrido_train(corpus)
    hashes = {"manifest": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
              "receta_semillas": hashlib.sha256(SEED_MANIFEST.read_bytes()).hexdigest(),
              "lexicon": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
              "semillas": [hashlib.sha256(t.encode()).hexdigest() for t in _semillas_reales()],
              "codigo": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT / "tools").rglob("*.py"))}}
    reporte = {"version": VERSION_METODO, "train": train, "hashes": hashes,
               "holdout": "no evaluado"}
    if args.evaluar_holdout:
        reporte["holdout"] = evaluar_holdout(corpus, umbral=train["final"]["umbral"], margen=train["final"]["margen"])
    print(json.dumps(reporte, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
