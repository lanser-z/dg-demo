"""End-to-end notebook execution test (lightweight nbconvert replacement).

Loads each .ipynb in notebook/ and runs every code cell in a fresh
namespace, with the notebook's own `sys.path` setup. Reports any
exception per cell. Used to verify the refactored step1.ipynb and
datahub_setup.ipynb execute cleanly.

Run:
    PYTHONPATH=src uv run python scripts/_verify_notebooks.py
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO = Path("/home/szs/Playground/dg-demo")
NB_DIR = REPO / "notebook"
NOTEBOOKS = ["step1.ipynb", "datahub_setup.ipynb"]


def _exec_cell(src: str, ns: dict) -> None:
    code = compile(src, "<cell>", "exec")
    exec(code, ns)


def verify(notebook_path: Path) -> tuple[int, int, list[str]]:
    # Both notebooks assume cwd == notebook/ (so os.path.dirname(os.getcwd())
    # walks up to the repo root, where data/ and src/ live). We mimic that.
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    import os
    os.chdir(NB_DIR)
    ns: dict = {"__name__": "__main__"}
    ok = 0
    fail = 0
    errors: list[str] = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
        if not src.strip():
            continue
        try:
            _exec_cell(src, ns)
            ok += 1
        except Exception:
            fail += 1
            tb = traceback.format_exc(limit=2)
            errors.append(f"cell {i} FAILED:\n{tb}")
    return ok, fail, errors


def main() -> int:
    rc = 0
    for name in NOTEBOOKS:
        path = NB_DIR / name
        if not path.exists():
            print(f"[skip] {name} not found")
            continue
        print(f"\n=== {name} ===")
        ok, fail, errors = verify(path)
        total = ok + fail
        print(f"  executed {total} code cells: {ok} ok, {fail} failed")
        for e in errors:
            print(f"\n{e}")
        if fail:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
