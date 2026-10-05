"""Executa o notebook com o Python atual, sem instalar kernel global."""

import os
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Cache e arquivos temporários ficam na pasta ignorada do projeto.
    temporary = ROOT / ".docker-local" / "jupyter"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["IPYTHONDIR"] = str(temporary / "ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(temporary / "runtime")
    manager = KernelManager(kernel_name="python3")
    # O kernel padrão do ipykernel usa o executável deste ambiente.
    manager.kernel_spec.argv[0] = sys.executable
    path = ROOT / "training" / "treinamento.ipynb"
    notebook = nbformat.read(path, as_version=4)
    executed = NotebookClient(notebook, km=manager, timeout=120,
                              resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.write(executed, path)
    print("Notebook executado e salvo com as saídas em training/treinamento.ipynb")
    for cell in executed.cells:
        if cell.cell_type == "code":
            for output in cell.get("outputs", []):
                if output.output_type == "stream":
                    print(output.text, end="")


if __name__ == "__main__":
    main()
