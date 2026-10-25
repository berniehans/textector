"""Smoke de wheel instalado en venv fuera del checkout, incluida su CLI real."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def main():
    wheel = Path(sys.argv[1]).resolve()
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="textector-wheel-") as tmp:
        root = Path(tmp)
        venv.EnvBuilder(with_pip=True).create(root / "venv")
        scripts = root / "venv" / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        executable = scripts / ("textector.exe" if os.name == "nt" else "textector")
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], cwd=root, env=env, check=True, capture_output=True)
        result = subprocess.run([str(executable), "analyze", "--archivo", str(source / "corpus/llm/a01.txt"), "--json", "--diagnostico"], cwd=root, env=env, check=True, capture_output=True, encoding="utf-8")
        data = json.loads(result.stdout)
        assert data["n_disponibles"] == 5
        assert data["version"] == "f4-integridad"
        assert data["diagnostico"]["no_concluyente"] is True
        assert data["resultado"]["compression"]["valor_bruto"]["n_seed_ia"] > 0
        # Verificar igualdad completa con ejecución del checkout.
        expected = subprocess.run([sys.executable, "-B", str(source / "tools/cli.py"), "analyze", "--archivo", str(source / "corpus/llm/a01.txt"), "--json", "--diagnostico"], cwd=root, env=env, check=True, capture_output=True, encoding="utf-8")
        assert data == json.loads(expected.stdout)
        portable = subprocess.run([str(executable), "analyze", "--archivo", str(source / "corpus/llm/a01.txt"), "--metodo", "f5", "--json"], cwd=root, env=env, check=True, capture_output=True, encoding="utf-8")
        portable_data = json.loads(portable.stdout)
        assert portable_data["version"] == "f5-portable-v1"
        assert portable_data["pesos_fijos"] == {"cliches_es": 0.25, "compression_positive_only": 0.3, "mattr": 0.45}
        expected_portable = subprocess.run([sys.executable, "-B", str(source / "tools/cli.py"), "analyze", "--archivo", str(source / "corpus/llm/a01.txt"), "--metodo", "f5", "--json"], cwd=root, env=env, check=True, capture_output=True, encoding="utf-8")
        assert portable_data == json.loads(expected_portable.stdout)
        print("wheel instalado: entry point, recursos, F4/F5 y paridad con checkout OK")


if __name__ == "__main__":
    main()
