"""The supplied objective template uses single-choice A-D options in Question."""
import re

TEST_TYPES = ("objective", "subjective", "mixed")


def validate_test_type(value):
    if not isinstance(value, str) or value not in TEST_TYPES:
        raise ValueError(
            "test_type must be objective, subjective or mixed."
        )


def objective_question(question, answer):
    """Parse the fixed template, retaining original spreadsheet values separately."""
    lines = question.strip().splitlines()
    starts = [(i, re.fullmatch(r"([A-D])\)\s*(.+)", line.strip()))
              for i, line in enumerate(lines)]
    options = [(i, match) for i, match in starts if match]
    if ([m.group(1) for _, m in options] != list("ABCD")
            or options[0][0] == 0
            or [i for i, _ in options] != list(range(len(lines) - 4, len(lines)))):
        raise ValueError("Objective questions require a stem followed by four lines labelled A), B), C), D).")
    choices = {m.group(1): m.group(2).strip() for _, m in options}
    if len({v.casefold() for v in choices.values()}) != 4:
        raise ValueError("Objective question options must be distinct.")
    key = str(answer).strip()
    if key in choices:
        correct = key
    else:
        match = re.fullmatch(r"([A-D])\)\s*(.+)", key)
        if not match or match.group(2).strip() != choices[match.group(1)]:
            raise ValueError("Objective answer key must identify exactly one matching option (A-D or label and text).")
        correct = match.group(1)
    return {"question_stem": "\n".join(lines[:options[0][0]]).strip(),
            "options": choices, "correct_option": correct}


def validate_question_type(row, test_type):
    has_options = bool(
        re.search(r"(?m)^\s*[A-D]\)\s*\S", row["Question"])
    )

    if test_type == "objective":
        parsed = objective_question(
            row["Question"],
            row["Answer Key"],
        )
        return {
            "question_type": "objective",
            **parsed,
        }

    if test_type == "subjective":
        if has_options:
            raise ValueError(
                "Subjective paper contains option-labelled questions; "
                "upload the paper to detect its type."
            )
        return {"question_type": "subjective"}

    if test_type == "mixed":
        if has_options:
            parsed = objective_question(
                row["Question"],
                row["Answer Key"],
            )
            return {
                "question_type": "objective",
                **parsed,
            }

        return {"question_type": "subjective"}

    raise ValueError(
        f"Unsupported test_type: {test_type!r}"
    )


def detect_paper_type(questions):
    """
    Classify every question independently and then determine the
    overall paper type.

    A paper may therefore be:
        objective
        subjective
        mixed

    The per-question question_type is the authoritative grading mode.
    """
    kinds = set()

    for row in questions:
        if re.search(
            r"(?im)(?:^|\s)[a-d]\)",
            row["Question"],
        ):
            try:
                parsed = objective_question(
                    row["Question"],
                    row["Answer Key"],
                )
            except ValueError as exc:
                raise ValueError(
                    f"Question {row['Question No']}: {exc}"
                ) from exc

            row.update(parsed)
            row["question_type"] = "objective"
            kinds.add("objective")

        else:
            row["question_type"] = "subjective"
            kinds.add("subjective")

    if kinds == {"objective"}:
        return "objective"

    if kinds == {"subjective"}:
        return "subjective"

    return "mixed"


def selected_option(answer, options):
    """Accept a label or a matching labelled choice, never semantic free text."""
    text = str(answer or "").strip()
    if text.upper() in options:
        return text.upper()
    match = re.fullmatch(r"([A-Da-d])\)\s*(.+)", text)
    if match and match.group(2).strip() == options.get(match.group(1).upper()):
        return match.group(1).upper()
    return None


def evaluate_objective(record, question):
    correct = question["correct_option"]
    selected = selected_option(record["candidate_answer"], question["options"])
    outcome = "Unanswered" if record["unanswered"] else "Correct" if selected == correct else "Incorrect"
    return {"awarded_marks": record["max_marks"] if outcome == "Correct" else 0,
            "correct_option": correct, "answer_status": outcome, "test_type": "objective",
            "justification": "Correct answer." if outcome == "Correct" else f"{outcome}. Correct option: {correct}."}
