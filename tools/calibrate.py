# Calibración F3-v2 de textector: 3 dominios, split por grupos y holdout fijo.
#
# Lee el corpus congelado (``corpus/manifest.csv`` + textos, 40 piezas en 3
# subcarpetas: ``human``, ``llm``, ``news``), puntúa cada texto con el
# pipeline F2 CONGELADO (los 5 checks + ``scoring.compute_indice``; NO
# retoca pesos ni transformaciones: ver docs/methodology.md) y ajusta el
# UMBRAL del índice con elección honesta:
#
# - Split por GRUPOS (unidad = AUTOR humano; pieza IA; grupo), no ad hoc:
#   * human: h14 == h17 (Pereda, mismo grupo); los demás autores tienen
#     un grupo propio. Nota: h08 y h16 comparten autor (Alas/Clarín) y
#     también grupo, pero ambos caen en holdout, así que ese grupo no
#     cruza train/holdout.
#   * llm (narrativa propia): a01..a10, un grupo por id de archivo.
#   * news (noticias sintéticas, clase ``llm`` + campo ``dominio``):
#     b01..b10 = UN SOLO grupo (Zenodo/SLM).
#   * HOLDOUT_V2 (fijo, elegido ya, no cambia): {h08, h16, h19, a05,
#     a07, b03}. El resto = TRAIN.
#   * Tensión declarada: el grupo Zenodo cubre b01..b10 y b03 está en
#     holdout, de modo que ese grupo queda repartido entre train y
#     holdout (limitación documentada en docs/calibration.md).
# - Barrido del umbral y LOGO-CV SOLO con TRAIN: barrido determinista de
#   (umbral, margen de abstención) + validación cruzada
#   leave-one-group-out dentro de TRAIN (el holdout nunca participa).
# - El HOLDOUT_V2 se abre UNA VEZ (``main()`` imprime el reporte final):
#   matriz TP/FP/TN/FN, desglose de FPs por subtipo humano (clásicos vs
#   modernos) y de FNs por dominio IA (narrativa propia vs noticias), y
#   abstenciones visibles (ids). Los tests NO abren el holdout (solo
#   split/seeds/manifest/determinismo).
#
# Semillas de compresión: ``corpus/seeds/seed_ia_es.txt`` y
# ``corpus/seeds/seed_hum_es.txt`` son concatenaciones EXACTAS (unidas por
# ``\\n\\n``) de los textos de TRAIN de su clase. El holdout NO aporta
# semillas. Con el holdout_v2 la semilla IA fue reconstruida: se retiró
# el bloque de a07 (ahora holdout); a05 ya estaba fuera y el resto de
# bloques corresponde a TRAIN v2. Estado F5: el check ``compression``
# recibe estas semillas ES reales inyectadas por ``puntuar`` (una carga
# por proceso, vía ``_semillas_reales``); el reporte del check etiqueta
# ``semillas: reales-es`` con el sha256 de cada semilla cruda.

# Determinista, stdlib, sin red. Reporte JSON con claves ordenadas.

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

__all__ = [
    "GRUPO_HUMANO", "GRUPO_IA", "HOLDOUT_V2", "HOLDOUT", "AREA_UMBRAL",
    "MARGENES", "CLASICOS", "GRUPOS_HUMANO", "cargar_corpus", "puntuar",
    "split_grupos", "evaluar_holdout", "main",
]

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.csv"
CONFIG = ROOT / "config" / "cliches_es.yaml"
SEED_IA = CORPUS / "seeds" / "seed_ia_es.txt"
SEED_HUM = CORPUS / "seeds" / "seed_hum_es.txt"

# Cargas únicas por proceso (semillas reales y léxico completo del config).
_SEMILLAS_REALES: tuple[str, str] | None = None
_LEXICON_COMPLETO: list[Any] | None = None

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


# ---------------------------------------------------------------------------
# Carga del corpus y puntuación (pipeline F2 congelado)
# ---------------------------------------------------------------------------

def _subcarpeta(pid: str) -> str:
    if pid.startswith("h"):
        return "human"
    if pid.startswith("a"):
        return "llm"
    if pid.startswith("b"):
        return "news"
    raise ValueError(f"id de corpus desconocido: {pid}")


def _dominio_ia(pid: str) -> str:
    """Dominio del texto: h* literatura PD; a* narrativa IA propia; b* noticias sintéticas."""
    if pid.startswith("h"):
        return "literatura_pd"
    if pid.startswith("a"):
        return "narrativa_propia"
    if pid.startswith("b"):
        return "noticias_sinteticas"
    return ""


def _grupo_de(pid: str) -> str:
    """Grupo de CV: autor humano; pieza IA; grupo único Zenodo para b."""
    if pid.startswith("h"):
        return GRUPOS_HUMANO[pid]
    if pid.startswith("a"):
        return pid          # un grupo por pieza (prompt propio)
    return "zenodo"         # b01..b10: un solo grupo (mismo generador)


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
            sub = _subcarpeta(pid)
            path = CORPUS / sub / f"{pid}.txt"
            fila = {k: (v or "").strip() for k, v in row.items()}
            fila["texto"] = path.read_text(encoding="utf-8")
            fila["dominio"] = _dominio_ia(pid)
            filas[pid] = fila
    if len(filas) != 40:
        raise ValueError(f"manifest con {len(filas)} filas; se esperaban 40")
    return filas


def _semillas_reales() -> tuple[str, str]:
    """Semillas ES reales (una carga por proceso; falla clara si faltan)."""
    global _SEMILLAS_REALES
    if _SEMILLAS_REALES is None:
        if not SEED_IA.is_file() or not SEED_HUM.is_file():
            faltan = SEED_IA.name if not SEED_IA.is_file() else SEED_HUM.name
            raise FileNotFoundError(
                f"semilla no encontrada: corpus/seeds/{faltan} (se exige para puntuar)"
            )
        _SEMILLAS_REALES = (
            SEED_IA.read_text(encoding="utf-8"),
            SEED_HUM.read_text(encoding="utf-8"),
        )
    return _SEMILLAS_REALES


def _lexicon_completo() -> list[Any]:
    """Léxico completo de config/cliches_es.yaml (misma fuente que el CLI).

    Antes ``puntuar`` usaba el mínimo embebido de ``build_lexicon()``, que
    NO es la señal que emite el CLI (léxico completo del config): la
    equivalencia CLI/calibrate exige la misma fuente.
    """
    global _LEXICON_COMPLETO
    if _LEXICON_COMPLETO is None:
        from tools.checks.cliches_es import phrases_from_parsed
        from tools.lexicon import parse_yaml_min

        _LEXICON_COMPLETO = phrases_from_parsed(
            parse_yaml_min(CONFIG.read_text(encoding="utf-8"))
        )
    return _LEXICON_COMPLETO


def puntuar(texto: str) -> dict[str, Any]:
    """Pipeline congelado con semillas ES reales y léxico completo del config.

    Misma señal que el CLI (misma fuente de semillas y de léxico); las
    semillas se cargan una vez por proceso y se reutilizan en las 40 piezas.
    """
    from tools.checks import burstiness, cliches_es, compression, mattr, uniformity
    from tools.scoring import compute_indice

    seed_ia, seed_hum = _semillas_reales()
    resultados = {
        "burstiness": burstiness.check(texto),
        "mattr": mattr.check(texto),
        "uniformity": uniformity.check(texto),
        "cliches_es": cliches_es.check(texto, lexicon=_lexicon_completo()),
        "compression": compression.check(texto, seed_ia=seed_ia, seed_hum=seed_hum),
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
        if pid in HOLDOUT_V2:
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

    # Grupos de TRAIN: por AUTOR humano; a en su pieza; b en grupo Zenodo.
    grupos: dict[str, list[str]] = {}
    for pid in train:
        grupos.setdefault(_grupo_de(pid), []).append(pid)

    # CV leave-one-group-out: umbral/margen del fold se elige con el resto.
    folded: list[dict[str, Any]] = []
    for grupo, pids in sorted(grupos.items()):
        calib = [p for p in train if p not in pids]
        test = pids
        mejor = _elegir(calib, idx_de, esperado)
        tpr, tnr = _tasas(test, corpus, mejor["umbral"], mejor["margen"], idx_de, esperado)
        folded.append(
            {"grupo": grupo, "piezas": pids, "umbral": mejor["umbral"],
             "margen": mejor["margen"], "tpr_fold": round(tpr, 4),
             "tnr_fold": round(tnr, 4)}
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
    """Matriz TP/FP/TN/FN del HOLDOUT_v2 con (umbral, margen) de TRAIN.

    Llámala UNA VEZ por proceso (``main()``): reporte honesto con los
    casos que falla, el desglose de FPs por subtipo humano (clásicos vs
    modernos) y de FNs por dominio IA (narrativa propia vs noticias), y
    las abstenciones visibles (ids). Los tests NO la invocan.
    """
    umbral = _UMBRAL_ELEGIDO["umbral"]
    margen = int(_UMBRAL_ELEGIDO["margen"])
    holdout = split_grupos(corpus)["holdout"]
    tp = tn = fp = fn = ab = 0
    fp_subtipo: dict[str, int] = {"clasicos": 0, "modernos": 0}
    fn_dominio: dict[str, int] = {"narrativa_propia": 0, "noticias_sinteticas": 0}
    abstenciones_ids: list[str] = []
    casos: list[dict[str, Any]] = []
    for pid in holdout:
        idx = _indice_de(corpus[pid]["texto"])
        pred = _prediccion(idx, umbral, margen)
        esperado = GRUPO_HUMANO if pid.startswith("h") else GRUPO_IA
        subtipo = "clasico" if pid in CLASICOS else "moderno"
        dominio = _dominio_ia(pid)
        if pred == "abstencion":
            ab += 1
            abstenciones_ids.append(pid)
        elif esperado == GRUPO_IA:
            if pred == GRUPO_IA:
                tp += 1
            else:
                fn += 1
                fn_dominio[dominio] += 1
        elif pred == GRUPO_IA:
            fp += 1
            clave = "clasicos" if subtipo == "clasico" else "modernos"
            fp_subtipo[clave] += 1
        else:
            tn += 1
        casos.append(
            {"id": pid, "indice": idx, "predicho": pred, "esperado": esperado,
             "subtipo_humano": subtipo if esperado == GRUPO_HUMANO else "",
             "dominio_ia": dominio}
        )
    humanos = [c for c in casos if c["esperado"] == GRUPO_HUMANO and c["predicho"] != "abstencion"]
    tasa_fp = (fp / len(humanos)) if humanos else None
    n_ia = sum(1 for c in casos if c["esperado"] == GRUPO_IA)
    tasa_fn = (fn / n_ia) if n_ia else None
    return {
        "umbral": umbral,
        "margen": margen,
        "matriz": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "tasa_fp_humanos": None if tasa_fp is None else round(tasa_fp, 4),
        "tasa_fn_ia": None if tasa_fn is None else round(tasa_fn, 4),
        "fp_humano_subtipo": fp_subtipo,
        "fn_ia_dominio": fn_dominio,
        "abstenciones": ab,
        "abstenciones_ids": abstenciones_ids,
        "casos": casos,
    }


_UMBRAL_ELEGIDO: dict[str, int | float] = {"umbral": 0, "margen": 0}


def main() -> int:
    """Ejecución completa: barrido+LOGO-CV en train, luego holdout_v2 UNA VEZ."""
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
    reporte["holdout_v2"] = evaluar_holdout(corpus)
    print(json.dumps(reporte, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
