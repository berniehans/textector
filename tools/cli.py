"""CLI de textector (F4): subcomando ``analyze`` con reporte explicable.

Uso:

    python tools/cli.py analyze (--archivo RUTA | --stdin) [--json] [--detallado]

Reutiliza el pipeline congelado F2 (los 5 checks de ``tools/checks/`` más
``tools/scoring.compute_indice``), el núcleo de texto ``tools/textector_core``
y el parser YAML-min ``tools/lexicon`` para cargar el léxico completo de
``config/cliches_es.yaml`` (que se pasa al check ``cliches_es``). NO duplica
lógica de scoring, checks ni parsing.

Errores manejados — archivo inexistente, YAML invalido, entrada vacia y
texto muy corto — imprimen UNA línea en stderr y terminan con exit code 1:
sin traceback y sin volcar el contenido del archivo leído.

Determinista, solo stdlib, sin red, sin escritura en disco.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pipeline import MINIMO_CHECKS, puntuar as puntuar_pipeline  # noqa: E402
from tools import f5 as f5_portable  # noqa: E402
from tools.resources import CONFIG, SEED_IA, SEED_HUM  # noqa: E402
from tools.checks.cliches_es import phrases_from_parsed  # noqa: E402
from tools.diagnostico import diagnostico_hibrido  # noqa: E402
from tools.estructura import eje_estructura  # noqa: E402
from tools.lexicon import MarkerError, parse_yaml_min  # noqa: E402
from tools.textector_core import tokenize  # noqa: E402

CONFIG_DEFECTO = CONFIG
SEED_IA_DEFECTO = SEED_IA
SEED_HUM_DEFECTO = SEED_HUM

MINIMO_CONGELADO = MINIMO_CHECKS


class ErrorCLI(Exception):
    """Error de uso/entrada: mensaje de UNA línea, exit 1, sin traceback."""


# ---------------------------------------------------------------------------
# Carga de entradas y config (I/O único del CLI)
# ---------------------------------------------------------------------------

def _leer_entrada(args: argparse.Namespace) -> str:
    """Texto crudo desde --archivo o --stdin. Errores: inexistente / vacia."""
    if getattr(args, "stdin", False):
        try:
            texto = sys.stdin.read()
        except (OSError, UnicodeError) as exc:
            raise ErrorCLI("no se pudo leer stdin como texto") from exc
    else:
        path = Path(args.archivo)
        if not path.is_file():
            raise ErrorCLI(f"archivo no encontrado: {path}")
        try:
            texto = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ErrorCLI("archivo con codificación no UTF-8 (decodificación falló)") from exc
        except OSError as exc:
            raise ErrorCLI(f"no se pudo leer el archivo ({type(exc).__name__})") from exc
    if not texto.strip():
        raise ErrorCLI("entrada vacia: no hay texto que analizar")
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def _cargar_lexicon(path: Path) -> list[Any]:
    """Carga config/cliches_es.yaml via tools.lexicon (fail-closed, sin volcado)."""
    if not path.is_file():
        raise ErrorCLI(f"config no encontrada: {path}")
    try:
        texto = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ErrorCLI(f"config ilegible o no UTF-8 ({type(exc).__name__})") from exc
    try:
        parsed = parse_yaml_min(texto)
    except MarkerError as exc:
        m = re.search(r"l[íi]nea\s+(\d+)", str(exc))
        num = m.group(1) if m else "n/d"
        raise ErrorCLI(
            f"config YAML invalido (línea {num}): formato no aceptado por YAML-min"
        ) from exc
    try:
        return phrases_from_parsed(parsed)
    except (ValueError, TypeError) as exc:
        # El mensaje de lexicon/checks puede citar la entrada cruda: no se
        # reenvía (no se volca contenido del archivo).
        raise ErrorCLI("config YAML invalido: entradas de léxico con formato inesperado") from exc


def _cargar_semillas(
    ruta_ia: Path = SEED_IA_DEFECTO,
    ruta_hum: Path = SEED_HUM_DEFECTO,
) -> tuple[str, str]:
    """Textos semilla (IA, humana) desde ``ROOT/corpus/seeds/``, UTF-8.

    Falla con ``ErrorCLI`` de UNA línea si falta o es ilegible cualquiera de
    las dos; nunca reenvía el contenido leído.
    """
    textos: list[str] = []
    for etiqueta, ruta in (("IA", ruta_ia), ("humana", ruta_hum)):
        if not ruta.is_file():
            raise ErrorCLI(f"semillas ({etiqueta}): archivo no encontrado: {ruta}")
        try:
            textos.append(ruta.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            raise ErrorCLI(
                f"semillas ({etiqueta}): archivo ilegible o no UTF-8 "
                f"({type(exc).__name__}): {ruta}"
            ) from exc
    if any(not tokenize(t) for t in textos):
        raise ErrorCLI("semillas inválidas: se exige contenido léxico en ambas")
    return textos[0], textos[1]


# ---------------------------------------------------------------------------
# Pipeline congelado (delegado: scoring + checks, sin duplicar lógica)
# ---------------------------------------------------------------------------

def _puntuar(
    texto: str,
    lexicon: list[Any],
    semillas: tuple[str, str],
) -> dict[str, Any]:
    """Pipeline f4 compartido con el léxico completo y las semillas reales.

    ``compression`` recibe las semillas (seed_ia, seed_hum) cargadas una vez
    por proceso, igual que ``tools/calibrate.py:puntuar``: misma señal, mismo
    índice por pieza.
    """
    return puntuar_pipeline(texto, lexicon, semillas)


# ---------------------------------------------------------------------------
# Presentación de resultados
# ---------------------------------------------------------------------------

def _resumen(informe: dict[str, Any]) -> str:
    base = (
        f"indice_llm={informe['indice_llm']} version={informe['version']} "
        f"n_disponibles={informe['n_disponibles']} semillas={informe['semillas']}"
    )
    if informe.get("version") == "f5-portable-v1":
        return (base + f" predicho={informe['predicho']} umbral={informe['umbral']} "
                f"banda_abstencion={informe['banda_abstencion']}")
    return base


def _detalle_check(nombre: str, r: dict[str, Any]) -> str:
    return (
        f"{nombre}: valor_bruto={json.dumps(dict(r['valor_bruto']), ensure_ascii=False)} "
        f"normalizado={r['normalizado']:.4f} peso={r['peso']:.4f} "
        f"contribucion={r['contribucion']:.4f} coverage={r['coverage']:.4f}"
    )


def _imprimir_humano(informe: dict[str, Any], detallado: bool) -> None:
    print(_resumen(informe))
    if not detallado:
        return
    if informe.get("version") == "f5-portable-v1":
        for nombre, r in informe["checks_portables"].items():
            print(f"{nombre}: q_bruto={informe['q_brutos'].get(nombre)} "
                  f"q_efectivo={informe['q_efectivos'].get(nombre, informe['q_efectivos'].get('compression_positive_only'))} "
                  f"contribucion={informe['contribuciones'].get(nombre, informe['contribuciones'].get('compression_positive_only'))}")
        print("auxiliares fuera del índice: " + ", ".join(
            informe["checks_auxiliares_fuera_del_indice"]))
        if informe["checks_insuficientes"]:
            print("insuficientes (F5 se abstiene): " + ", ".join(informe["checks_insuficientes"]))
        return
    for nombre, r in informe["resultado"].items():
        print(_detalle_check(nombre, r))
    insuficientes = [
        n
        for n in ("burstiness", "mattr", "uniformity", "cliches_es", "compression")
        if n not in informe["resultado"]
    ]
    if insuficientes:
        print("insuficientes (excluidos del índice): " + ", ".join(insuficientes))


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textector",
        description=(
            "Índice heurístico explicable (0-100) de señales de escritura"
            " típica de LLM en texto español. NO es una probabilidad ni una"
            " prueba de autoría: usar solo como pre-filtro con revisión humana."
            " La evaluación externa de F4 es limitada y registró falsos positivos."
        ),
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    analyze = sub.add_parser(
        "analyze",
        help="puntúa un texto (--archivo RUTA o --stdin, solo una).",
    )
    origen = analyze.add_mutually_exclusive_group(required=True)
    origen.add_argument("--archivo", metavar="RUTA", help="leer el texto de un archivo UTF-8")
    origen.add_argument(
        "--stdin", action="store_true", dest="stdin", help="leer el texto de stdin"
    )
    analyze.add_argument("--config", type=Path, default=None, metavar="RUTA",
                         help="yaml-min del léxico (por defecto config/cliches_es.yaml)")
    analyze.add_argument(
        "--json", action="store_true", help="emitir el informe completo como JSON"
    )
    analyze.add_argument(
        "--detallado",
        action="store_true",
        help="desglose por check (valor bruto, normalizado, peso, contribución, coverage)",
    )
    analyze.add_argument(
        "--metodo", choices=("f4", "f5"), default="f4",
        help="perfil a usar: f4 histórico (predeterminado) o f5 portable",
    )
    analyze.add_argument(
        "--diagnostico",
        action="store_true",
        help="diagnóstico de dos ejes (prosa vs estructura) con categoría y nota",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point del CLI: invokingState maneja errores con exit 1, una línea."""
    args = _construir_parser().parse_args(argv)
    try:
        texto = _leer_entrada(args)
        lexicon = _cargar_lexicon(args.config or CONFIG_DEFECTO)
        semillas = _cargar_semillas()  # carga ÚNICA por proceso
        if args.metodo == "f5":
            if args.diagnostico:
                raise ErrorCLI("--diagnostico describe F4; F5 reporta sus auxiliares fuera del índice")
            informe = f5_portable.puntuar(texto, lexicon, semillas)
        else:
            informe = _puntuar(texto, lexicon, semillas)
            if (informe["indice_llm"] is None
                    or informe["n_disponibles"] != MINIMO_CONGELADO):
                raise ErrorCLI(
                    "texto muy corto: el pipeline congelado no alcanzó la cobertura "
                    "mínima para puntuar"
                )
        informe = {**informe, "semillas": "reales-es"}
    except ErrorCLI as exc:
        mensaje = " ".join(str(exc).splitlines())
        print(f"error: {mensaje}", file=sys.stderr)
        return 1
    diag = None
    if getattr(args, "diagnostico", False) and args.metodo == "f4":
        diag = diagnostico_hibrido(informe, eje_estructura(texto))
        informe = {**informe, "diagnostico": diag}
    if args.json:
        print(json.dumps(informe, sort_keys=True, ensure_ascii=False))
    else:
        _imprimir_humano(informe, detallado=args.detallado)
        if diag is not None:
            print(
                "diagnostico: categoria=%s prosa=%s estructura=%s no_concluyente=%s"
                % (
                    diag.get("categoria"),
                    diag.get("prosa", {}).get("indice_llm"),
                    diag.get("estructura", {}).get("valor"),
                    diag.get("no_concluyente"),
                )
            )
            print("nota: " + str(diag.get("nota", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
