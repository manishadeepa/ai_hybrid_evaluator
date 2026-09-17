from datetime import datetime
from backend.repositories.manual_evaluation_repository import ManualEvaluationRepository


class ManualEvaluationService:
    """Business logic for manual candidate evaluation."""

    def __init__(self, repository=None):
        self.repository = repository or ManualEvaluationRepository()

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
    ) -> dict:
        """Validate question-wise marks, calculate totals, and save evaluation."""

        if not candidate_id:
            raise ValueError("Candidate ID is required.")

        if not assessment_name:
            raise ValueError("Assessment name is required.")

        if not test_name:
            raise ValueError("Test name is required.")

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
            "assessment_name": assessment_name,
            "test_name": test_name,
            "evaluation_type": "manual",
            "evaluated_at": datetime.now().isoformat(timespec="seconds"),
            "total_marks": total_awarded,
            "max_marks": total_marks,
            "percentage": overall_percentage,
            "questions": questions,
        }

        return self.repository.save(evaluation)
