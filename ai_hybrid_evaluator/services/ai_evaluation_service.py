


from pathlib import Path
import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from openai import AzureOpenAI


def _load_client():
    """
    Create the Azure OpenAI client from the project's .env file.
    """

    project_dir = Path(__file__).resolve().parents[2]
    env_file = project_dir / ".env"

    load_dotenv(env_file, override=True)

    api_key = os.getenv("AZURE_API_KEY")
    endpoint = os.getenv("AZURE_ENDPOINT")
    deployment = os.getenv("AZURE_DEPLOYMENT_NAME")

    if not api_key:
        raise ValueError("AZURE_API_KEY is missing from .env")

    if not endpoint:
        raise ValueError("AZURE_ENDPOINT is missing from .env")

    if not deployment:
        raise ValueError("AZURE_DEPLOYMENT_NAME is missing from .env")

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2024-10-21",
    )

    return client, deployment


def build_evaluation_prompt(
    question,
    answer_key,
    candidate_answer,
    max_marks,
    metadata=None,
):
    """
    Build the same evaluation prompt used by the notebook engine.
    """

    metadata_block = ""

    if metadata:
        metadata_block = f"""
Additional context (for reference only, do not evaluate against these directly):
Knowledge Type: {metadata.get("knowledge_type")}
RBT Level: {metadata.get("rbt_level")}
Domain: {metadata.get("domain")}
"""

    return f"""You are an academic answer evaluator. Evaluate the student's answer strictly based on meaning, correctness, relevance, and completeness - NOT exact wording or text similarity.

QUESTION:
{question}

REFERENCE ANSWER (answer key):
{answer_key}

STUDENT ANSWER:
{candidate_answer}

MAXIMUM MARKS: {max_marks}
{metadata_block}

Rules:
- Never award more than {max_marks} marks.
- Give partial credit for partially correct answers.
- Do not penalize different wording if the meaning is technically equivalent.
- Reduce marks for incorrect technical statements or missing important concepts.
- Do not award marks for irrelevant content.

Respond with ONLY valid JSON (no markdown code fences, no extra text) in exactly this schema:
{{
    "awarded_marks": <number>,
    "percentage": <number 0-100>,
    "evaluation": {{
        "correctness": "<short assessment>",
        "relevance": "<short assessment>",
        "completeness": "<short assessment>",
        "strengths": ["...", "..."],
        "missing_points": ["...", "..."],
        "incorrect_points": ["..."]
    }},
    "justification": "<detailed explanation of the marks awarded>"
}}"""


def _evaluate_answer(client, deployment, record):
    """
    Evaluate one normalized candidate answer.
    """

    if record["unanswered"]:
        return {
            "question_no": record["question_no"],
            "question": record["question"],
            "maximum_marks": record["max_marks"],
            "awarded_marks": 0,
            "percentage": 0,
            "evaluation": {
                "correctness": "N/A",
                "relevance": "N/A",
                "completeness": "N/A",
                "strengths": [],
                "missing_points": ["No answer provided"],
                "incorrect_points": [],
            },
            "justification": "Question not attempted by the candidate.",
        }

    prompt = build_evaluation_prompt(
        question=record["question"],
        answer_key=record["answer_key"],
        candidate_answer=record["candidate_answer"],
        max_marks=record["max_marks"],
        metadata=record["metadata"],
    )

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
    )

    raw_content = response.choices[0].message.content

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"AI did not return valid JSON for "
            f"{record['question_no']}: {e}\n"
            f"Raw response: {raw_content}"
        )

    awarded = parsed["awarded_marks"]

    if awarded < 0 or awarded > record["max_marks"]:
        raise ValueError(
            f"Invalid awarded_marks {awarded} for "
            f"{record['question_no']} "
            f"(max was {record['max_marks']})"
        )

    parsed["question_no"] = record["question_no"]
    parsed["question"] = record["question"]
    parsed["maximum_marks"] = record["max_marks"]

    return parsed


def _evaluate_with_retry(
    client,
    deployment,
    record,
    max_retries=3,
    delay_seconds=2,
):
    """
    Evaluate one answer with bounded retry handling.
    """

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return _evaluate_answer(
                client,
                deployment,
                record,
            )

        except Exception as e:
            last_error = e

            if attempt < max_retries:
                time.sleep(delay_seconds)

    raise last_error


def _find_answer_key_column(answer_key_df):
    """
    Find the question column in the answer-key workbook.
    """

    for column in answer_key_df.columns:
        normalized = str(column).strip().lower()

        if normalized in {
            "question",
            "questions",
            "question text",
        }:
            return column

    return None


def _build_answer_key_lookup(answer_key_df):
    """
    Build question -> answer-key lookup.

    Supports the notebook's original format where each question
    is a column header and the answer is in the first row.

    Also supports a normal Question / Answer table.
    """

    lookup = {}

    question_column = _find_answer_key_column(answer_key_df)

    # Format 1:
    # Question | Answer
    if question_column is not None:

        answer_column = None

        for column in answer_key_df.columns:
            normalized = str(column).strip().lower()

            if normalized in {
                "answer",
                "answer key",
                "answer_key",
                "reference answer",
                "reference_answer",
            }:
                answer_column = column
                break

        if answer_column is not None:

            for _, row in answer_key_df.iterrows():

                question = str(
                    row[question_column]
                ).strip()

                if not question or question.lower() == "nan":
                    continue

                answer = row[answer_column]

                if pd.isna(answer):
                    answer = ""

                lookup[question] = str(answer).strip()

            return lookup

    # Format 2:
    # each question is a column header and the first row
    # contains the answer key.
    if len(answer_key_df) > 0:

        first_row = answer_key_df.iloc[0]

        for column in answer_key_df.columns:

            question = str(column).strip()

            answer = first_row[column]

            if pd.isna(answer):
                answer = ""

            lookup[question] = str(answer).strip()

    return lookup


def _load_question_data(question_paper_path):
    """
    Load the Question Paper metadata.

    The Question Paper Answer Key column, if present, is ignored.
    """

    question_df = pd.read_excel(question_paper_path)

    required_columns = [
        "Question No",
        "Question",
        "Marks",
        "CO",
        "LO",
        "Knowledge Type",
        "Domain",
        "RBT level",
    ]

    missing = [
        column
        for column in required_columns
        if column not in question_df.columns
    ]

    if missing:
        raise ValueError(
            "Question Paper is missing required columns: "
            + ", ".join(missing)
        )
    
    question_lookup = {}

    for _, row in question_df.iterrows():

        question = str(row["Question"]).strip()

        question_lookup[question] = {
            "question_no": row["Question No"],
            "max_marks": row["Marks"],
            "co": row["CO"],
            "lo": row["LO"],
            "knowledge_type": row["Knowledge Type"],
            "domain": row["Domain"],
            "rbt_level": row["RBT level"],
          "answer_key": row["Answer Key"],
        }

    return question_lookup


def _load_candidate_data(candidate_response_path):
    """
    Load candidate responses.

    Supports the current Reflex candidate-response format as well
    as the notebook's original wide Excel format.
    """

    candidate_df = pd.read_excel(candidate_response_path)

    # Current Reflex response format:
    # Question No | Question | Marks | ... | Candidate Answer
    if "Candidate Answer" in candidate_df.columns:

        records = []

        candidate_name = candidate_response_path.stem
        candidate_id = candidate_response_path.stem

        for _, row in candidate_df.iterrows():

            raw_answer = row["Candidate Answer"]

            unanswered = (
                pd.isna(raw_answer)
                or str(raw_answer).strip() == ""
            )

            candidate_answer = (
                None
                if unanswered
                else str(raw_answer).strip()
            )

            records.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_name,
                    "question_no": row["Question No"],
                    "question": str(row["Question"]).strip(),
                    "candidate_answer": candidate_answer,
                    "unanswered": unanswered,
                }
            )

        return records

    # Original notebook wide format.
    metadata_columns = [
        "ID",
        "Start time",
        "Completion time",
        "Email",
        "Name",
        "Last modified time",
    ]

    question_columns = [
        column
        for column in candidate_df.columns
        if column not in metadata_columns
    ]

    records = []

    for _, candidate_row in candidate_df.iterrows():

        candidate_id = candidate_row.get(
            "ID",
            candidate_response_path.stem,
        )

        candidate_name = candidate_row.get(
            "Name",
            candidate_response_path.stem,
        )

        for question_text in question_columns:

            raw_answer = candidate_row[question_text]

            unanswered = (
                pd.isna(raw_answer)
                or str(raw_answer).strip() == ""
            )

            candidate_answer = (
                None
                if unanswered
                else str(raw_answer).strip()
            )

            records.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_name,
                    "question_no": None,
                    "question": str(question_text).strip(),
                    "candidate_answer": candidate_answer,
                    "unanswered": unanswered,
                }
            )

    return records


def evaluate_candidate(
    question_paper_path,
    candidate_response_path,
    answer_key_path=None,
    max_retries=3,
):
    """
    Evaluate one candidate using:

    1. Question Paper
    2. Candidate Response
    3. Answer Key (optional separate file or embedded in Question Paper)

    Returns detailed question-wise results and candidate summary.
    """

    question_paper_path = Path(question_paper_path)
    candidate_response_path = Path(candidate_response_path)
    
    for path, label in [
        (question_paper_path, "Question Paper"),
        (candidate_response_path, "Candidate Response"),
        ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} not found: {path}"
            )

    client, deployment = _load_client()

    question_lookup = _load_question_data(
        question_paper_path
    )

    # If separate answer key file is provided, override the answer keys
    if answer_key_path and Path(answer_key_path).exists():
        try:
            ak_df = pd.read_excel(answer_key_path)
            ak_lookup = _build_answer_key_lookup(ak_df)
            for q_text, q_data in question_lookup.items():
                if q_text in ak_lookup and ak_lookup[q_text]:
                    q_data["answer_key"] = ak_lookup[q_text]
        except Exception as e:
            print(f"Warning: could not parse separate answer key: {e}")

    candidate_records = _load_candidate_data(
        candidate_response_path
    )

    normalized_records = []

    for record in candidate_records:

        question_text = record["question"].strip()

        if question_text not in question_lookup:
            raise ValueError(
                f"Candidate question was not found in "
                f"Question Paper: {question_text}"
            )

        meta = question_lookup[question_text]

        normalized_records.append(
            {
                "candidate_id": record["candidate_id"],
                "candidate_name": record["candidate_name"],
                "question_no": meta["question_no"],
                "question": question_text,
                "answer_key": meta["answer_key"],
                "max_marks": meta["max_marks"],
                "candidate_answer": record["candidate_answer"],
                "unanswered": record["unanswered"],
                "metadata": {
                    "co": meta["co"],
                    "lo": meta["lo"],
                    "knowledge_type": meta["knowledge_type"],
                    "domain": meta["domain"],
                    "rbt_level": meta["rbt_level"],
                },
            }
        )

    evaluation_results = []
    evaluation_errors = []

    for record in normalized_records:

        try:

            result = _evaluate_with_retry(
                client,
                deployment,
                record,
                max_retries=max_retries,
            )

            result["candidate_id"] = record["candidate_id"]
            result["candidate_name"] = record["candidate_name"]
            result["co"] = record["metadata"]["co"]
            result["lo"] = record["metadata"]["lo"]
            result["knowledge_type"] = record["metadata"]["knowledge_type"]
            result["domain"] = record["metadata"]["domain"]
            result["rbt_level"] = record["metadata"]["rbt_level"]
            result["candidate_answer"] = record["candidate_answer"]
            result["unanswered"] = record["unanswered"]

            evaluation_results.append(result)

        except Exception as e:

            evaluation_errors.append(
                {
                    "candidate_id": record["candidate_id"],
                    "candidate_name": record["candidate_name"],
                    "question_no": record["question_no"],
                    "error": str(e),
                }
            )

    if not evaluation_results and evaluation_errors:
        raise RuntimeError(
            "AI evaluation failed for all candidate responses. "
            + str(evaluation_errors)
        )

    results_df = pd.DataFrame(
        [
            {
                "candidate_id": result["candidate_id"],
                "candidate_name": result["candidate_name"],
                "question_no": result["question_no"],
                "question": result["question"],
                "co": result["co"],
                "lo": result["lo"],
                "knowledge_type": result["knowledge_type"],
                "domain": result["domain"],
                "rbt_level": result["rbt_level"],
                "maximum_marks": result["maximum_marks"],
                "candidate_answer": result["candidate_answer"],
                "awarded_marks": result["awarded_marks"],
                "percentage": result["percentage"],
                "correctness": result.get("evaluation", {}).get(
                    "correctness", ""
                ),
                "relevance": result.get("evaluation", {}).get(
                    "relevance", ""
                ),
                "completeness": result.get("evaluation", {}).get(
                    "completeness", ""
                ),
                "strengths": "; ".join(
                    result.get("evaluation", {}).get(
                        "strengths", []
                    )
                ),
                "missing_points": "; ".join(
                    result.get("evaluation", {}).get(
                        "missing_points", []
                    )
                ),
                "incorrect_points": "; ".join(
                    result.get("evaluation", {}).get(
                        "incorrect_points", []
                    )
                ),
                "justification": result["justification"],
                "unanswered": result["unanswered"],
            }
            for result in evaluation_results
        ]
    )

    summary_rows = []

    for candidate_id, group in results_df.groupby(
        "candidate_id"
    ):

        total_max = group["maximum_marks"].sum()
        total_awarded = group["awarded_marks"].sum()

        num_questions = len(group)
        num_answered = int(
            (~group["unanswered"]).sum()
        )
        num_unanswered = int(
            group["unanswered"].sum()
        )

        summary_rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": group[
                    "candidate_name"
                ].iloc[0],
                "total_maximum_marks": total_max,
                "total_awarded_marks": total_awarded,
                "overall_percentage": round(
                    (total_awarded / total_max) * 100,
                    2,
                )
                if total_max > 0
                else 0,
                "num_questions": num_questions,
                "num_answered": num_answered,
                "num_unanswered": num_unanswered,
                "average_marks_per_question": round(
                    total_awarded / num_questions,
                    2,
                )
                if num_questions > 0
                else 0,
            }
        )

    candidate_summary_df = pd.DataFrame(
        summary_rows
    )

    if not candidate_summary_df.empty:
        candidate_summary_df["rank"] = (
            candidate_summary_df[
                "overall_percentage"
            ]
            .rank(
                ascending=False,
                method="min",
            )
            .astype(int)
        )

        candidate_summary_df = (
            candidate_summary_df
            .sort_values("rank")
            .reset_index(drop=True)
        )

    def build_group_analysis(
        df,
        group_col,
    ):
        rows = []

        for group_value, group in df.groupby(
            group_col
        ):

            max_marks = group[
                "maximum_marks"
            ].sum()

            obtained = group[
                "awarded_marks"
            ].sum()

            rows.append(
                {
                    group_col: group_value,
                    "num_questions": group[
                        "question_no"
                    ].nunique(),
                    "maximum_marks": max_marks,
                    "obtained_marks": obtained,
                    "attainment_percentage": round(
                        (obtained / max_marks) * 100,
                        2,
                    )
                    if max_marks > 0
                    else 0,
                    "average_score": round(
                        group[
                            "awarded_marks"
                        ].mean(),
                        2,
                    ),
                }
            )

        return (
            pd.DataFrame(rows)
            .sort_values(group_col)
            .reset_index(drop=True)
        )

    co_analysis_df = build_group_analysis(
        results_df,
        "co",
    )

    lo_analysis_df = build_group_analysis(
        results_df,
        "lo",
    )

    rbt_analysis_df = build_group_analysis(
        results_df,
        "rbt_level",
    )

    return {
        "results": evaluation_results,
        "results_df": results_df,
        "candidate_summary_df": candidate_summary_df,
        "co_analysis_df": co_analysis_df,
        "lo_analysis_df": lo_analysis_df,
        "rbt_analysis_df": rbt_analysis_df,
        "errors": evaluation_errors,
    }