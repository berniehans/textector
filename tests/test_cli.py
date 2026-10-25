"""CLI de textector (F4): especificación ejecutable vía subprocess.

Casos: (a) JSON válido parseable; (b) archivo inexistente; (c) config/YAML
invalido; (d) texto muy corto; (e) --detallado con las claves del desglose.
Los archivos temporales viven en ``tempfile.mkdtemp()`` (fuera del árbol del
proyecto) y se limpian en ``tearDown``. Solo stdlib.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "tools" / "cli.py"
CONFIG = ROOT / "config" / "cliches_es.yaml"

# Prosa de prueba: > 50 tokens (minimo de clichés_es) y suficientes oraciones
# de longitudes variadas para que los 5 checks del pipeline congelado corran.
TEXTO_VALIDO = """\
El primer invierno de la casa nueva empezó con un error de calculo de mi tío, que
compró leña de más. Vieron llegar el camión dos veces el mismo día. La pila se
acercó al techo del depósito.

—¿Y esta leña quién la pide? —preguntó el vecino de enfrente, que custodiaba el
portón con la misma disciplina con que guardaba los meses.

—La segunda camioneta —respondió mi tío sin girarse— es un problema sin dueño;
la primera era mía y se resolvió.

El pueblo registró el exceso con la precisión que registra los pragmáticos de su
historia doméstica, sin tono, sin queja: una cifra más en la memoria de invierno.
La niebla de la sierra no aceptaba horarios. Al anochecer, el ruido de la leña
secándose llenaba el Patio de la casa donde el libro del padre estuvo adosado
a la espina por la ventana del cuarto de estudio. Y como la leña al fin acabó,
en marzo, quedaron solo las marcas: esta es la lista breve y sincera de los que
encontramos al desarmar el depósito, ordenada por el orden en que aparecieron.

Primero: dos soportes con las huellas del formón. Después: la pizarra de los
turnos, ilegible por la sal. Después: tres boletos de la cooperativa, doblados
con la costumbre de los años. Después: un imán con el escudo del colegio.
Al final, pegado en la base, el papel que mi tío llamaba el inventario del
exceso y que yo guardo hasta hoy: una lista corta, sin nombres, con el peso
de todo lo que sobró, calculado a puntero y firmado con la fecha de la compra
equivocada que nos dejó, a todos, la leña doble.

—¿Y si vuelve el frío? —preguntó mi madre, y nadie contestó, porque el frío,
como la leña, y como el exceso, también tiene su dueño en otras temporadas.
Nadie supo qué contestar, y el depósito siguió cerrado hasta la primavera.
"""


class TestCli(unittest.TestCase):
    """Executa el CLI con subprocess y workspace temporal fuera del proyecto."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="textector-cli-tests-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(CLI_PATH), "analyze", "--config", str(CONFIG), *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=stdin,
            cwd=str(self.tmp),
        )

    def _archivo(self, nombre: str, contenido: str) -> str:
        ruta = self.tmp / nombre
        ruta.write_text(contenido, encoding="utf-8")
        return str(ruta)

    def test_a_json_valid_parseable(self) -> None:
        """(a) --json produce stdout JSON parseable con indice 0..100."""
        ruta = self._archivo("texto.txt", TEXTO_VALIDO)
        res = self._run("--archivo", ruta, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        indice = data["indice_llm"]
        self.assertIsInstance(indice, int)
        self.assertGreaterEqual(indice, 0)
        self.assertLessEqual(indice, 100)

    def test_b_archivo_inexistente_falla(self) -> None:
        """(b) archivo inexistente: exit != 0, una línea de error en stderr."""
        ruta = str(self.tmp / "definitivamente_inexistente.txt")
        res = self._run("--archivo", ruta)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(res.stdout.strip())
        self.assertTrue(res.stderr.strip())

    def test_c_yaml_invalido_falla(self) -> None:
        """(c) config YAML invalido: exit != 0, sin volcar contenido."""
        conf = self._archivo("malo.yaml", "version: 1\nfoo: no-es-lista-ni-int\n")
        ruta = self._archivo("texto.txt", TEXTO_VALIDO)
        res = self._run("--archivo", ruta, "--config", conf)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(res.stdout.strip())
        # Del contenido del yaml solo puede aparecer el nombre, no su valor.
        self.assertNotIn("no-es-lista-ni-int", res.stderr)

    def test_d_texto_muy_corto_falla_sin_score(self) -> None:
        """(d) texto muy corto: exit != 0 y ningún dígito de score en stdout."""
        ruta = self._archivo("corto.txt", "Hola mundo; esto es solamente prueba corta.\nHola de nuevo mundo.\n")
        res = self._run("--archivo", ruta)
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(any(ch.isdigit() for ch in res.stdout))

    def test_e_detallado_muestra_desglose(self) -> None:
        """(e) --detallado imprime las claves del desglose por check."""
        ruta = self._archivo("texto.txt", TEXTO_VALIDO)
        res = self._run("--archivo", ruta, "--detallado")
        self.assertEqual(res.returncode, 0, res.stderr)
        for clave in ("valor_bruto", "normalizado", "peso", "contribucion", "coverage"):
            self.assertIn(clave, res.stdout)


if __name__ == "__main__":
    unittest.main()
