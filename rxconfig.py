import os
from pathlib import Path

# Development reload should watch source code, not saved answers,
# feedback JSON, generated Excel files, or temporary persistence files.
_project_root = Path(__file__).resolve().parent
_reload_files = ["rxconfig.py"]

for _package in ("ai_hybrid_evaluator", "backend"):
    for _source in sorted((_project_root / _package).rglob("*.py")):
        _relative = _source.relative_to(_project_root)
        if "data" in _relative.parts or "__pycache__" in _relative.parts:
            continue
        _reload_files.append(_relative.as_posix())

os.environ["REFLEX_HOT_RELOAD_OVERRIDE_PATHS"] = ":".join(_reload_files)
import reflex as rx

config = rx.Config(
    app_name="ai_hybrid_evaluator",
    bun_path=Path(r"C:\Program Files\nodejs\npm.cmd"),
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)