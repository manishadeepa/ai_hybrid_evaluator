import os
from pathlib import Path

# Development reload should watch source code directories, not saved answers,
# feedback JSON, generated Excel files, or temporary persistence files.
# Uvicorn expects valid directory paths in reload_dirs, not individual file paths.
_project_root = Path(__file__).resolve().parent
_reload_dirs = [
    _dir.relative_to(_project_root).as_posix()
    for _package in ("ai_hybrid_evaluator", "backend")
    if (_dir := _project_root / _package).is_dir()
]

os.environ["REFLEX_HOT_RELOAD_OVERRIDE_PATHS"] = ":".join(_reload_dirs)
os.environ["REFLEX_USE_GRANIAN"] = "false"
import reflex as rx

config = rx.Config(
    app_name="ai_hybrid_evaluator",
    bun_path=Path(r"C:\Program Files\nodejs\npm.cmd"),
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="indigo",
                radius="large",
            )
        ),
    ]
)