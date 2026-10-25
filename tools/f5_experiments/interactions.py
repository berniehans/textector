"""Analyze predeclared factorial interactions from the development run."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "validation/f5-narrative-experiment-v1"
RESULTS = EXPERIMENT / "factorial-results.json"
OUTPUT = EXPERIMENT / "factorial-interactions.json"
REPORT = EXPERIMENT / "factorial-report.md"
FACTORS = {"L2": 0, "C2-v2": 1, "M100-fallback50": 2}
PROFILES = {
    f"P{a}{b}{c}": (a, b, c)
    for a in (0, 1) for b in (0, 1) for c in (0, 1)
}
REPLICATES = 2000
SEED = 25102027


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(rows: list[dict[str, Any]], profile: str, weight_key: str | None) -> float | None:
    if not rows:
        return None
    weights = [float(row[weight_key]) if weight_key else 1.0 for row in rows]
    denom = sum(weights)
    if denom <= 0:
        return None
    detected = sum(w for row, w in zip(rows, weights)
                   if row[profile]["prediction"] == "ia")
    return detected / denom


def _contrasts(rows: list[dict[str, Any]], weight_key: str | None) -> dict[str, float | None]:
    cell_means = {profile: _metric(rows, profile, weight_key) for profile in PROFILES}
    result: dict[str, float | None] = {}
    for size in (1, 2, 3):
        from itertools import combinations
        for names in combinations(FACTORS, size):
            indexes = [FACTORS[name] for name in names]
            contrast = 0.0
            valid = True
            for profile, bits in PROFILES.items():
                mean = cell_means[profile]
                if mean is None:
                    valid = False
                    break
                sign = 1
                for index in indexes:
                    sign *= 1 if bits[index] else -1
                contrast += sign * mean / 4.0
            result[" × ".join(names)] = contrast if valid else None
    return result


def _bootstrap(rows: list[dict[str, Any]], cluster_key: str, weight_key: str | None,
               replicates: int = REPLICATES) -> dict[str, dict[str, Any]]:
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        clusters[str(row[cluster_key])].append(row)
    keys = sorted(clusters)
    if not keys:
        return {}
    rng = random.Random(SEED)
    values: dict[str, list[float]] = defaultdict(list)
    for _ in range(replicates):
        sample = [row for key in (rng.choice(keys) for _ in keys) for row in clusters[key]]
        for name, value in _contrasts(sample, weight_key).items():
            if value is not None:
                values[name].append(value)
    point = _contrasts(rows, weight_key)
    answer = {}
    for name, estimate in point.items():
        boot = sorted(values[name])
        if estimate is None or not boot:
            answer[name] = {"estimate": estimate, "ci95_low": None, "ci95_high": None}
            continue
        answer[name] = {
            "estimate": estimate,
            "ci95_low": boot[int(0.025 * (len(boot) - 1))],
            "ci95_high": boot[int(0.975 * (len(boot) - 1))],
        }
    return answer


def _analysis(results: dict[str, Any]) -> dict[str, Any]:
    if results.get("uses_reserved_data") is not False:
        raise ValueError("interaction analysis is restricted to development results")
    if results.get("status") != "development_experiment_complete_not_confirmatory":
        raise ValueError("unexpected scoring-result status")
    cases = results["cases"]
    ai_es = [row for row in cases if row["label"] == "ai" and row["manual_language"] == "espanol"]
    humans = [row for row in cases if row["label"] == "human"]
    by_source: dict[str, Any] = {}
    for source in sorted({row["author_or_model"] for row in ai_es}):
        subset = [row for row in ai_es if row["author_or_model"] == source]
        by_source[source] = {
            "n_rows": len(subset),
            "n_prompt_clusters": len({row["prompt_id"] for row in subset}),
            "sampling_weighted_exploratory": _bootstrap(subset, "prompt_id", "sampling_weight"),
        }
    return {
        "analysis_id": "f5-narrative-experiment-v1-factorial-interactions",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "source_result_sha256": _sha(RESULTS),
        "uses_reserved_data": False,
        "design": "2x2x2; contrast is sum(y*product(signs))/4 on the detection-proportion scale",
        "interaction_hypotheses": {
            "H0": "the factor effects are additive on detection proportions",
            "H1": "at least one predeclared factorial interaction differs from zero",
            "interpretation": "two-sided 95% cluster-bootstrap intervals are exploratory; exclusion of zero is not confirmatory and does not override human-error gates",
        },
        "bootstrap": {"replicates": REPLICATES, "seed": SEED,
                      "ai_clusters": "prompt_id; unequal language-audit sampling weights retained",
                      "human_clusters": "author_or_model"},
        "ai_manually_verified_spanish_sampling_weighted": {
            "n_rows": len(ai_es),
            "n_prompt_clusters": len({row["prompt_id"] for row in ai_es}),
            "overall": _bootstrap(ai_es, "prompt_id", "sampling_weight"),
            "by_source": by_source,
        },
        "human_false_positive_rate": {
            "n_rows": len(humans),
            "n_author_clusters": len({row["author_or_model"] for row in humans}),
            "overall": _bootstrap(humans, "author_or_model", None),
        },
        "limitations": [
            "Development-only analysis; no confirmatory inference.",
            "The language-audit design is stratified with unequal inclusion probabilities; retaining weights does not replace a design-specific confirmatory analysis.",
            "Small numbers of prompt and author clusters make the bootstrap intervals exploratory.",
        ],
    }


def _fmt(value: float | None) -> str:
    return "n/d" if value is None else f"{100*value:.1f}%"


def _report(results: dict[str, Any], interactions: dict[str, Any]) -> str:
    data = results["data"]
    profiles = results["factorial_profiles"]
    lines = [
        "# Informe experimental F5 para narración en español",
        "",
        f"**Protocolo:** `{results['protocol_id']}`  ",
        f"**Corrida:** {results['evaluated_utc']}  ",
        f"**Estado:** {results['status']}  ",
        f"**Umbral/margen:** {results['threshold']}/{results['abstention_margin']} (congelados)  ",
        "**Conjunto reservado:** no leído ni puntuado.",
        "",
        "## Pregunta, hipótesis y contrahipótesis",
        "",
        "- **H0 global:** al menos una puerta de promoción falla en la población objetivo.",
        "- **H1 global:** FP humana ≤5%, cobertura humana ≥80% y detección IA ≥80% en cada fuente, con límites unilaterales del 95% que también cumplen las puertas.",
        "- **H0 de señal:** al menos una fuente no mejora ≥5 puntos porcentuales frente a B0. **H1:** cada fuente mejora ≥5 pp.",
        "- **H0 de interacción:** los efectos L2, C2-v2 y M100 son aditivos en la escala de proporciones. **H1:** existe al menos una interacción factorial distinta de cero.",
        "- La interpretación de detección es la del prefiltro experimental; no prueba autoría individual.",
        "",
        "## Método ejecutado",
        "",
        f"Se puntuaron {data['full_development_n']} documentos de desarrollo para la referencia B0/F4 y {data['factorial_n']} en la matriz 2×2×2. Se retiraron {data['c2_seed_rows_removed_from_ai_panel']} filas IA correspondientes a {data['c2_seed_prompts_removed']} prompts usados por C2-v2. Se compararon B0, L2, C2-v2, M100 con fallback M50 entre 50–99 tokens y todas sus combinaciones. C2 usa ocho documentos por clase, 64 pares emparejados por bytes y mediana; 1024 bytes es el análisis principal, 512/1280 son sensibilidad.",
        f"La auditoría lingüística manual comprende {data['manual_language_reviewed_n']} filas: {data['manual_language_label_counts']['espanol']} español, {data['manual_language_label_counts']['ingles']} inglés y {data['manual_language_label_counts']['mixto']} mixtas. El panel IA español contiene {data['manually_verified_spanish_ai_rows_in_factorial']} filas y {data['verified_spanish_ai_prompt_clusters']} prompts; las filas sin etiqueta manual se presentan solo de forma descriptiva.",
        "",
        "## Resultados por perfil",
        "",
        "Detección IA en español se pondera por el diseño de auditoría y se define sobre todos los casos IA, incluidas abstenciones. FP y cobertura humana usan todos los 120 textos humanos.",
        "",
        "| Perfil | L2 | C2-v2 | M100 | FP humana | Cobertura humana | Detección IA ES ponderada | Fuentes ≥80% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for profile, item in profiles.items():
        hm = item["human_development"]["metrics"]
        ai = item["ai_manually_verified_spanish_sampling_weighted"]["metrics"]
        by = item["ai_manually_verified_spanish_by_checkpoint_weighted"]
        rates = [x["metrics"]["ai_detection_on_all_ai"] for x in by.values()]
        qualified = sum(x is not None and x >= 0.8 for x in rates)
        f = item["factors"]
        lines.append(f"| {profile} | {'Sí' if f['L2'] else 'No'} | {'Sí' if f['C2-v2'] else 'No'} | {'Sí' if f['M100-fallback50'] else 'No'} | {_fmt(hm['human_fp_on_all_humans'])} | {_fmt(hm['human_decision_coverage'])} | {_fmt(ai['ai_detection_on_all_ai'])} | {qualified}/8 |")
    lines += [
        "",
        "### Detección por fuente, porcentaje",
        "",
        "| Perfil | Arcee Blitz | Mistral Nemo | Gemma SPPO | Llama 3.1 | Gemma Ataraxy | Hermes 3 | Gemma 2 9B | Mistral Small |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    short_names = ["Arcee", "Nemo", "SPPO", "Llama", "Ataraxy", "Hermes", "Gemma", "Mistral S"]
    for profile, item in profiles.items():
        by = item["ai_manually_verified_spanish_by_checkpoint_weighted"]
        values = [x["metrics"]["ai_detection_on_all_ai"] for x in by.values()]
        lines.append("| " + profile + " | " + " | ".join(_fmt(x) for x in values) + " |")
    lines += [
        "",
        "El orden de las ocho columnas sigue las fuentes del manifiesto: " + ", ".join(short_names) + ".",
        "",
        "## Contrastes e hipótesis de mejora",
        "",
        "| Perfil vs B0 | Mínimo delta entre fuentes | Máximo delta | ≥5 pp en todas las fuentes |",
        "|---|---:|---:|---:|",
    ]
    for profile, item in results["five_pp_improvement_hypotheses"].items():
        deltas = list(item["delta_detection_by_checkpoint"].values())
        lines.append(f"| {profile} | {_fmt(min(deltas))} | {_fmt(max(deltas))} | {'Sí' if item['point_estimate_supports_H1'] else 'No'} |")
    lines += [
        "",
        "### Efectos principales e interacciones factoriales",
        "",
        "La tabla incluye los efectos principales (un factor) y los contrastes de interacción (dos o tres factores); estos últimos evalúan H0/H1 de aditividad. Se calcularon como contraste factorial de detección, con bootstrap por prompt IA y por autor humano (2000 réplicas). Son intervalos bilaterales exploratorios; la auditoría estratificada y el bajo número de conglomerados impiden interpretarlos como confirmación.",
        "",
        "| Efecto/contraste IA español ponderado | Estimación (pp) | IC exploratorio 95% (pp) |",
        "|---|---:|---:|",
    ]
    for name, stat in interactions["ai_manually_verified_spanish_sampling_weighted"]["overall"].items():
        lines.append(f"| {name} | {100*stat['estimate']:.2f} | {100*stat['ci95_low']:.2f} a {100*stat['ci95_high']:.2f} |")
    lines += [
        "",
        "## Controles y puertas",
        "",
        f"B0 completo: detección IA descriptiva { _fmt(results['controls']['b0_full_development']['metrics']['ai_detection_on_all_ai']) }, FP humana {_fmt(results['controls']['b0_full_development']['metrics']['human_fp_on_all_humans'])}, cobertura humana {_fmt(results['controls']['b0_full_development']['metrics']['human_decision_coverage'])}.",
        f"F4 completo: detección IA descriptiva {_fmt(results['controls']['f4_full_development']['metrics']['ai_detection_on_all_ai'])}, FP humana {_fmt(results['controls']['f4_full_development']['metrics']['human_fp_on_all_humans'])}, cobertura humana {_fmt(results['controls']['f4_full_development']['metrics']['human_decision_coverage'])}.",
        "",
        "Ningún perfil pasa todas las puertas en esta pantalla de desarrollo. Incluso donde las tasas puntuales humanas pasan, ninguna opción alcanza ≥80% de detección en las ocho fuentes. Los límites de confianza para promoción no se consideran aprobados: el resultado correcto es **datos insuficientes para promoción**, no selección de un ganador.",
        "",
        "## Sensibilidad C2 y conclusión",
        "",
    ]
    for length, item in sorted(results["c2_seed_length_sensitivity"].items(), key=lambda x: int(x[0])):
        lines.append(f"- {length} bytes: delta medio de q frente a 1024 = {item['q_delta_vs_1024_mean']:.4f}; detección española ponderada con C2 = {_fmt(item['ai_manually_verified_spanish_sampling_weighted']['metrics']['ai_detection_on_all_ai'])}.")
    lines += [
        "",
        "La evidencia de desarrollo no justifica promover F5 ni cambiar umbral/margen. M100 aporta detección pero falla claramente las puertas humanas; L2 respeta las puertas humanas por puntos en P100/P110 pero no resuelve varias fuentes; C2-v2 tiene un efecto pequeño. Mantener B0 congelado y diseñar confirmación independiente, con más autores/prompts y auditoría lingüística suficiente. No usar este análisis para calibrar el umbral.",
        "",
        "## Reproducibilidad e integridad",
        "",
        f"- Reserva leída: `{results['uses_reserved_data']}`.",
        f"- Umbral y margen retocados: `{results['retuned_threshold_or_margin']}`.",
        f"- SHA-256 del lock C2: `{results['lock_sha256']}`.",
        f"- SHA-256 del manifiesto factorial: `{results['scoring_manifest_sha256']}`.",
        f"- SHA-256 del código del runner: `{results['code_hashes']['tools\\f5_experiments\\run.py']}`.",
        f"- SHA-256 de resultados completos: `{_sha(RESULTS)}`.",
        f"- SHA-256 de interacciones: `{_sha(OUTPUT)}`.",
        "- Artefactos: `factorial-results.json` (por caso y resumen), `factorial-case-scores.jsonl`, `factorial-interactions.json`, manifiesto y lock bajo `validation/f5-narrative-experiment-v1/`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    interactions = _analysis(results)
    OUTPUT.write_text(json.dumps(interactions, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
    REPORT.write_text(_report(results, interactions), encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)),
                      "interactions": str(OUTPUT.relative_to(ROOT)),
                      "result_sha256": _sha(RESULTS),
                      "interaction_sha256": _sha(OUTPUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
