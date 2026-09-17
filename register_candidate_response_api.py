from pathlib import Path

path = Path(r".\backend\main.py")
text = path.read_text(encoding="utf-8")

old_import = "from backend.api.manual_evaluation import router as manual_evaluation_router"
new_import = """from backend.api.manual_evaluation import router as manual_evaluation_router
from backend.api.candidate_responses import router as candidate_responses_router"""

if old_import not in text:
    raise SystemExit("Target import not found. No changes made.")

text = text.replace(old_import, new_import, 1)

old_include = "app.include_router(manual_evaluation_router)"
new_include = """app.include_router(manual_evaluation_router)
app.include_router(candidate_responses_router)"""

if old_include not in text:
    raise SystemExit("Target router registration not found. No changes made.")

text = text.replace(old_include, new_include, 1)

path.write_text(text, encoding="utf-8")
print("SUCCESS: Candidate Response API router registered.")
