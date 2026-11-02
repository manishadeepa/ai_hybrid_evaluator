from datetime import datetime
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository


class ManualEvaluationService:
    """Business logic for manual candidate evaluation."""

    def __init__(self, repository=None, tests=None):
        self.repository = repository or ManualEvaluationRepository()
        if tests is None:
            from backend.repositories.test_repository import TestRepository
            from backend.services.test_service import TestService

            data_dir = self.repository.storage.file_path.parent
            tests = TestService(TestRepository(data_dir / "tests.json"))
        self.tests = tests

    def get_evaluation(
        self,
        candidate_id: str,
        assessment_name: str,
        test_name: str,
    ) -> dict | None:
        """Return a previously saved manual evaluation."""
        
        if not candidate_id:
            raise ValueError("Candidate ID is required.")

        if not assessment_name:
            raise ValueError("Assessment name is required.")

        if not test_name:
            raise ValueError("Test name is required.")

        return self.repository.get_by_key(
            candidate_id=candidate_id,
            assessment_name=assessment_name,
            test_name=test_name,
        )

    def evaluate_and_save(
        self,
        candidate_id: str,
        assessment_name: str,
        test_name: str,
        responses: list[dict],
        *,
        test_id: str,
        facilitator_id: str,
        role: str,
    ) -> dict:
        """Validate question-wise marks, calculate totals, and save evaluation."""

        if not candidate_id:
            raise ValueError("Candidate ID is required.")

        if not assessment_name:
            raise ValueError("Assessment name is required.")

        if not test_name:
            raise ValueError("Test name is required.")

        test = self.tests.authorize_evaluation(test_id, facilitator_id, role)
        assessment = self.tests.get_assessment(test_id)
        if test["test_name"] != test_name or assessment["name"] != assessment_name:
            raise ValueError("Evaluation identity does not match the selected assessment/test.")

        if not responses:
            raise ValueError("No candidate responses were provided.")

        questions = []
        total_marks = 0.0
        total_awarded = 0.0

        for index, response in enumerate(responses):
            question_no = str(
                response.get("q_no")
                or response.get("question_no")
                or index + 1
            )

            question = str(response.get("question", "") or "")
            candidate_response = str(
                response.get("response")
                or response.get("candidate_answer")
                or ""
            )

            try:
                max_marks = float(
                    response.get("max_marks")
                    or response.get("marks")
                    or 0
                )
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid maximum marks for question {question_no}."
                )

            try:
                awarded_marks = float(
                    response.get("awarded_marks")
                    or response.get("manual_marks")
                    or response.get("ai_score")
                    or 0
                )
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid awarded marks for question {question_no}."
                )

            if max_marks < 0:
                raise ValueError(
                    f"Maximum marks cannot be negative for question {question_no}."
                )

            if awarded_marks < 0:
                raise ValueError(
                    f"Awarded marks cannot be negative for question {question_no}."
                )

            if awarded_marks > max_marks:
                raise ValueError(
                    f"Marks awarded for question {question_no} "
                    f"cannot exceed maximum marks ({max_marks})."
                )

            percentage = (
                round((awarded_marks / max_marks) * 100, 1)
                if max_marks > 0
                else 0.0
            )

            justification = str(
                response.get("justification")
                or response.get("remarks")
                or ""
            )

            questions.append(
                {
                    "q_no": question_no,
                    "question": question,
                    "candidate_response": candidate_response,
                    "marks_obtained": awarded_marks,
                    "max_marks": max_marks,
                    "percentage": percentage,
                    "justification": justification,
                    "CO": response.get("CO", response.get("co", "")),
                    "LO": response.get("LO", response.get("lo", "")),
                    "Knowledge Type": response.get(
                        "Knowledge Type",
                        response.get("knowledge_type", ""),
                    ),
                    "Domain": response.get(
                        "Domain",
                        response.get("domain", ""),
                    ),
                    "RBT level": response.get(
                        "RBT level",
                        response.get("rbt_level", ""),
                    ),
                }
            )

            total_awarded += awarded_marks
            total_marks += max_marks

        total_awarded = round(total_awarded, 2)
        total_marks = round(total_marks, 2)

        overall_percentage = (
            round((total_awarded / total_marks) * 100, 1)
            if total_marks > 0
            else 0.0
        )

        evaluation = {
            "candidate_id": candidate_id,
            "assessment_id": test["assessment_id"],
            "test_id": test_id,
            "assessment_name": assessment_name,
            "test_name": test_name,
            "evaluation_type": "manual",
            "evaluated_at": datetime.now().isoformat(timespec="seconds"),
            "total_marks": total_awarded,
            "max_marks": total_marks,
            "percentage": overall_percentage,
            "questions": questions,
        }

        return self.repository.save(
            evaluation,
            facilitator_id=facilitator_id,
            role=role,
        )

    def update_review_result(self, candidate_id, assessment_name, test_name, test_id, question_no, *,
                             awarded_marks=None, justification=None, remarks=None,
                             facilitator_id, role):
        test = self.tests.authorize_evaluation(test_id, facilitator_id, role)
        assessment = self.tests.get_assessment(test_id)
        if test["test_name"] != test_name or assessment["name"] != assessment_name:
            raise ValueError("Evaluation identity does not match the selected assessment/test.")
        evaluation = self.repository.get_by_key(candidate_id, assessment_name, test_name)
        if evaluation is None:
            raise ValueError("No saved manual evaluation exists for this candidate and test.")
        if evaluation.get("test_id") != test_id or evaluation.get("assessment_id") != test["assessment_id"]:
            raise ValueError("Saved manual evaluation has no matching canonical test identity.")
        questions = evaluation.get("questions")
        if not isinstance(questions, list):
            raise ValueError("Saved manual evaluation questions are invalid.")
        question = next(
            (row for row in questions
             if str(row.get("q_no", "")).casefold() == str(question_no).casefold()),
            None,
        )
        if question is None:
            raise ValueError("Question is not part of the saved manual evaluation.")
        if awarded_marks is not None:
            try:
                marks = float(awarded_marks)
                maximum = float(question.get("max_marks"))
            except (TypeError, ValueError):
                raise ValueError("Review marks must be valid numbers.") from None
            if not 0 <= marks <= maximum:
                raise ValueError(f"Review marks must be between 0 and {maximum}.")
            question["marks_obtained"] = marks
            question["percentage"] = round(100 * marks / maximum, 1) if maximum else 0.0
        if justification is not None:
            question["justification"] = justification
        if remarks is not None:
            question["remarks"] = remarks
        evaluation["total_marks"] = round(sum(float(row["marks_obtained"]) for row in questions), 2)
        evaluation["max_marks"] = round(sum(float(row["max_marks"]) for row in questions), 2)
        evaluation["percentage"] = (
            round(evaluation["total_marks"] / evaluation["max_marks"] * 100, 1)
            if evaluation["max_marks"] else 0.0
        )
        return self.repository.save(evaluation, facilitator_id=facilitator_id, role=role)
