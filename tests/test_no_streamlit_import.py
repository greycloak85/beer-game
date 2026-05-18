"""ENG-01: the engine layer (engine/, ai/, config/) MUST NOT import streamlit.
Walk each .py file's AST and reject any Import or ImportFrom node naming streamlit.
"""
import ast
from pathlib import Path
import pytest

# Directories that constitute the "engine layer" -- anything below this line
# must remain stdlib-only so pytest can run determinism tests headlessly.
ENGINE_DIRS = [
    "beergame/engine",
    "beergame/ai",
    "beergame/config",
]


def _streamlit_imports_in(path: Path) -> list[str]:
    """Return list of human-readable strings describing any streamlit import in `path`."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        pytest.fail(f"Could not parse {path}: {e}")
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "streamlit" or alias.name.startswith("streamlit."):
                    bad.append(f"{path}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "streamlit" or node.module.startswith("streamlit.")):
                names = ", ".join(a.name for a in node.names)
                bad.append(f"{path}:{node.lineno}: from {node.module} import {names}")
    return bad


@pytest.mark.parametrize("subdir", ENGINE_DIRS)
def test_engine_layer_does_not_import_streamlit(subdir):
    """ENG-01: zero streamlit imports anywhere under the engine layer."""
    root = Path(subdir)
    assert root.exists(), f"expected engine layer directory {subdir} to exist"
    bad: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        bad.extend(_streamlit_imports_in(py_file))
    if bad:
        pytest.fail(
            f"Streamlit imports found in engine layer ({subdir}):\n  "
            + "\n  ".join(bad)
            + "\n\nThe engine, AI, and config layers are pure-Python by contract "
              "(ENG-01). If you need to surface diagnostics, return warning data on "
              "GameState and let the UI layer format it with st.warning."
        )


def test_engine_layer_directories_exist():
    """Sanity guard: if a future refactor renames a directory, fail loudly here
    instead of silently passing the parametric test with an empty file list."""
    for subdir in ENGINE_DIRS:
        p = Path(subdir)
        assert p.exists() and p.is_dir(), f"expected directory {subdir}"
        py_files = list(p.rglob("*.py"))
        assert py_files, f"expected at least one .py file under {subdir}"
