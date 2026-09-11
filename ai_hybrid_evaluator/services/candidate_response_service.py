"""Candidate Response Service — persists submitted candidate answers to Excel."""

from pathlib import Path
from datetime import datetime
import pandas as pd


def save_candidate_response(
    candidate_id: str,
    candidate_name: str,
    assessment_name: str,
    test_name: str,
    questions: list[dict],
    answers: dict,
) -> str:
    """Save the candidate's submitted answers as an Excel response file."""

    output_dir = Path("uploaded_files") / "candidate_responses"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for question in questions:
        question_id = question["id"]

        rows.append({
            "Question No": question["title"],
            "Question": question["text"],
            "Marks": question["marks"],
            "CO": question["co"],
            "LO": question["lo"],
            "Knowledge Type": question["knowledge_type"],
            "Domain": question["category"],
            "RBT level": question["rbt_level"],
            "Candidate Answer": answers.get(str(question_id), ""),
        })

    df = pd.DataFrame(rows)

    safe_candidate = candidate_name.replace(" ", "_")
    safe_test = test_name.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{safe_candidate}_{safe_test}_{timestamp}_Response.xlsx"
    output_path = output_dir / filename

    df.to_excel(output_path, index=False)

    return str(output_path)


def _safe_slug(text: str) -> str:
    """Normalize text for fuzzy filename matching: lowercase, spaces and hyphens to underscore."""
    import re
    return re.sub(r"[^a-z0-9_]", "", text.lower().replace(" ", "_").replace("-", "_"))


def find_candidate_response_file(
    candidate_id: str = "",
    candidate_name: str = "",
    assessment_name: str = "",
    test_name: str = "",
) -> Path | None:
    """Find the candidate response file in uploaded_files/candidate_responses/
    strictly matching candidate_id or candidate_name, and test_name.
    Returns None if no matching file exists. Never reuses another candidate's response.
    """
    output_dir = Path("uploaded_files") / "candidate_responses"
    if not output_dir.exists():
        return None

    id_slug = _safe_slug(candidate_id) if candidate_id else ""
    name_slug = _safe_slug(candidate_name) if candidate_name else ""
    test_slug = _safe_slug(test_name) if test_name else ""

    # Must specify a candidate to search
    if not id_slug and not name_slug:
        return None

    files = list(output_dir.glob("*.xlsx"))
    if not files:
        return None

    matched: list[Path] = []

    for f in files:
        f_slug = _safe_slug(f.stem)

        # Candidate MUST match: either ID or Name
        cand_match = False
        if id_slug and (id_slug in f_slug or id_slug.replace("_", "") in f_slug.replace("_", "")):
            cand_match = True
        elif name_slug and (name_slug in f_slug or name_slug.replace("_", "") in f_slug.replace("_", "")):
            cand_match = True

        if not cand_match:
            continue

        # Test MUST match if specified
        if test_slug:
            test_match = False
            clean_test = test_slug.replace("_", "")
            clean_f = f_slug.replace("_", "")
            if test_slug in f_slug or clean_test in clean_f:
                test_match = True
            if not test_match:
                continue

        matched.append(f)

    if not matched:
        return None

    return max(matched, key=lambda p: p.stat().st_mtime)


def get_latest_candidate_response(
    candidate_id: str = "",
    candidate_name: str = "",
    assessment_name: str = "",
    test_name: str = "",
) -> dict:
    """Load the latest candidate response file from candidate_response_service
    and return structured response data for Facilitator UI.
    Returns empty dict if no matching response file is found.
    """
    path = find_candidate_response_file(
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        assessment_name=assessment_name,
        test_name=test_name,
    )
    if path is None:
        return {}

    try:
        df = pd.read_excel(path)
        responses = []
        for _, row in df.iterrows():
            responses.append({
                "q_no": str(row.get("Question No", "") or ""),
                "question": str(row.get("Question", "") or ""),
                "response": str(row.get("Candidate Answer", "") or ""),
                "ai_score": "",
                "max_marks": str(row.get("Marks", "") or ""),
                "justification": "",
            })
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y, %I:%M %p")
        return {
            "submitted_on": mtime,
            "excel_file": path.name,
            "responses": responses,
            "ai_score": "—",
            "percentage": "—",
            "file_path": str(path),
        }
    except Exception:
        return {}