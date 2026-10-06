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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    filename = f"{safe_candidate}_{safe_test}_{timestamp}_Response.xlsx"
    output_path = output_dir / filename

    # Keep answers on the first sheet for existing readers. Identity is explicit.
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Responses", index=False)
        pd.DataFrame([{
            "candidate_id": str(candidate_id), "candidate_name": str(candidate_name),
            "assessment_name": assessment_name, "test_name": test_name,
        }]).to_excel(writer, sheet_name="Submission", index=False)

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
    require_assessment_scope: bool = False,
) -> Path | None:
    """Find the candidate response file in uploaded_files/candidate_responses/
    strictly matching candidate_id or candidate_name, and test_name.
    Returns None if no matching file exists. Never reuses another candidate's response.
    """
    if require_assessment_scope and (not candidate_id or not assessment_name or not test_name):
        raise ValueError("Strict lookup requires candidate ID, assessment and test")
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
        # Never use a known mismatched identity, even in legacy lookup mode.
        try:
            with pd.ExcelFile(f) as workbook:
                identity = (pd.read_excel(workbook, sheet_name="Submission", dtype=str).fillna("")
                            if "Submission" in workbook.sheet_names else None)
        except Exception:
            continue
        if identity is not None:
            if len(identity) != 1:
                continue
            metadata = identity.iloc[0].to_dict()
            if assessment_name and metadata.get("assessment_name") != assessment_name:
                continue
            if test_name and metadata.get("test_name") != test_name:
                continue
            if candidate_id:
                identity_matches = metadata.get("candidate_id") == str(candidate_id)
            else:
                identity_matches = metadata.get("candidate_name") == candidate_name
            if identity_matches:
                matched.append(f)
            continue
        if require_assessment_scope:
            # A filename cannot prove assessment ownership for old workbooks.
            continue
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
    require_assessment_scope: bool = False,
) -> dict:
    """
    Load a submitted candidate response for Facilitator evaluation.

    Canonical response lifecycle data is the primary source of truth.
    Existing Excel response files remain as a compatibility fallback.
    """

    # ------------------------------------------------------------
    # 1. CANONICAL BACKEND RESPONSE
    # ------------------------------------------------------------
    try:
        from backend.repositories.response_repository import ResponseRepository

        repository = ResponseRepository()
        records = repository.get_all()

        matches = []

        for record in records:
            # Evaluation must never expose an unfinished/disqualified attempt.
            if record.get("status") != "Submitted":
                continue

            # Candidate identity.
            if candidate_id:
                if str(record.get("candidate_id", "")).casefold() != str(candidate_id).casefold():
                    continue
            elif candidate_name:
                if str(record.get("candidate_name", "")).casefold() != str(candidate_name).casefold():
                    continue
            else:
                continue

            # Assessment identity.
            if assessment_name:
                if str(record.get("assessment_name", "")).casefold() != str(assessment_name).casefold():
                    continue

            # Test identity.
            if test_name:
                if str(record.get("test_name", "")).casefold() != str(test_name).casefold():
                    continue

            matches.append(record)

        if matches:
            # There should normally be one canonical session for this
            # candidate/assessment/test. If legacy data contains more than
            # one matching record, prefer the latest submitted one.
            record = max(
                matches,
                key=lambda r: str(r.get("submitted_at", "") or ""),
            )

            answers = record.get("answers", {})
            questions = record.get("questions", [])

            responses = []

            # Post-test presentation must use the ORIGINAL question-paper
            # numbering, not the randomized candidate attempt order.
            # This changes display/export order only. Stored questions,
            # question IDs and candidate answers remain untouched.
            import re

            def _post_test_question_sort_key(question):
                raw = str(
                    question.get("title")
                    or question.get("id")
                    or ""
                )
                match = re.search(r"\d+", raw)
                return int(match.group()) if match else 10**9

            ordered_questions = sorted(
                questions,
                key=_post_test_question_sort_key,
            )

            for question in ordered_questions:
                question_id = question.get("id")

                responses.append({
                    "q_no": str(
                        question.get("title")
                        or question_id
                        or ""
                    ),
                    "question": str(question.get("text", "") or ""),
                    "response": str(
                        answers.get(str(question_id), "") or ""
                    ),
                    "ai_score": "",
                    "max_marks": str(question.get("marks", "") or ""),
                    "justification": "",
                    "CO": str(question.get("co", "") or ""),
                    "LO": str(question.get("lo", "") or ""),
                    "Knowledge Type": str(
                        question.get("knowledge_type", "") or ""
                    ),
                    "Domain": str(question.get("category", "") or ""),
                    "RBT level": str(question.get("rbt_level", "") or ""),
                })

            response_file = str(record.get("response_file", "") or "")
            submitted_at = str(record.get("submitted_at", "") or "")

            submitted_on = submitted_at

            if submitted_at:
                try:
                    submitted_on = datetime.fromisoformat(
                        submitted_at.replace("Z", "+00:00")
                    ).strftime("%d %b %Y, %I:%M %p")
                except (ValueError, TypeError):
                    pass

            return {
                "submitted_on": submitted_on,
                "excel_file": (
                    Path(response_file).name
                    if response_file
                    else ""
                ),
                "responses": responses,
                "ai_score": "—",
                "percentage": "—",
                "file_path": response_file,
            }

    except (ValueError, OSError, KeyError, TypeError):
        # Preserve compatibility with the existing Excel-based response
        # mechanism if canonical data cannot be read.
        pass

    # ------------------------------------------------------------
    # 2. EXISTING EXCEL FALLBACK
    # ------------------------------------------------------------
    path = find_candidate_response_file(
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        assessment_name=assessment_name,
        test_name=test_name,
        require_assessment_scope=require_assessment_scope,
    )

    if path is None:
        return {}

    try:
        df = pd.read_excel(path).fillna("")

        responses = []

        for _, row in df.iterrows():
            responses.append({
                "q_no": str(row.get("Question No", "") or ""),
                "question": str(row.get("Question", "") or ""),
                "response": str(row.get("Candidate Answer", "") or ""),
                "ai_score": "",
                "max_marks": str(row.get("Marks", "") or ""),
                "justification": "",
                "CO": str(row.get("CO", "") or ""),
                "LO": str(row.get("LO", "") or ""),
                "Knowledge Type": str(row.get("Knowledge Type", "") or ""),
                "Domain": str(row.get("Domain", "") or ""),
                "RBT level": str(row.get("RBT level", "") or ""),
            })

        mtime = datetime.fromtimestamp(
            path.stat().st_mtime
        ).strftime("%d %b %Y, %I:%M %p")

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
