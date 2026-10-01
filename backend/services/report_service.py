"""Read-only, canonical-ID test reports over the authoritative result facade."""
from copy import deepcopy
from datetime import datetime, timezone
import re
from backend.services.evaluation_result_service import EvaluationResultService
from backend.services.assessment_service import _PERSISTENCE_LOCK


class ReportService:
    def __init__(self, results=None):
        self.results = results or EvaluationResultService()

    def catalog(self, assessment_id, *, facilitator_id="", admin=False, include_candidates=True):
        if not isinstance(assessment_id, str) or not assessment_id.strip():
            raise ValueError("Select a persisted assessment before downloading a report.")
        with _PERSISTENCE_LOCK:
            assessments = self.results._read(self.results.assessments.repository)
            assessment = next((a for a in assessments if a['assessment_id'] == assessment_id), None)
            if assessment is None:
                raise ValueError("The selected assessment no longer exists.")
            owners = assessment.get('facilitator_ids', [assessment.get('facilitator_id')])
            if not admin and (not facilitator_id or facilitator_id not in owners):
                raise ValueError("You are not authorized to report on this assessment.")
            tests = [t for t in self.results._read(self.results.assessments.tests.repository)
                     if t['assessment_id'] == assessment_id]
            candidates = []
            if include_candidates:
                # Historic finalized results remain selectable after membership changes.
                finalized = self.results.list_results(assessment_id=assessment_id)
                ids = set(assessment.get("assigned_candidates", [])) | {r["candidate_id"] for r in finalized}
                candidates = [c for c in self.results._candidate_rows() if c["candidate_id"] in ids]
            return deepcopy(dict(assessment=assessment, tests=tests, candidates=candidates))

    def build(self, assessment_id, test_id, candidate_id=None, *, facilitator_id="", admin=False):
        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError("Select exactly one test.")
        if candidate_id is not None and (not isinstance(candidate_id, str) or not candidate_id.strip()):
            raise ValueError("Select a candidate.")
        with _PERSISTENCE_LOCK:
            catalog = self.catalog(assessment_id, facilitator_id=facilitator_id, admin=admin, include_candidates=False)
            test = next((t for t in catalog['tests'] if t['test_id'] == test_id), None)
            if test is None:
                raise ValueError("The selected test does not belong to this assessment.")
            rows = self.results.list_results(assessment_id=assessment_id, test_id=test_id,
                                             candidate_id=candidate_id)
            if not rows:
                raise ValueError("No finalized evaluation results are available for this selection.")
            # Defense in depth: never export a result outside the requested identity.
            if any(r['assessment_id'] != assessment_id or r['test_id'] != test_id or
                   (candidate_id is not None and r['candidate_id'] != candidate_id) for r in rows):
                raise ValueError("Result identity does not match the selected report.")
            return deepcopy(dict(assessment_id=assessment_id, assessment_name=catalog['assessment']['name'],
                test_id=test_id, test_name=test['test_name'],
                test_category='Summative' if test.get('is_final') else 'Formative',
                test_type=test.get('test_type'), generated_at=datetime.now(timezone.utc).isoformat(),
                candidates=rows))

    @staticmethod
    def filename(report):
        def safe(value):
            return re.sub(r'[^\w-]+', '_', str(value), flags=re.UNICODE).strip('_')[:55] or 'report'
        return 'Report_' + safe(report['assessment_name']) + '_' + safe(report['test_name']) + '_' + safe(report['test_id']) + '.pdf'

    def download(self, *args, **kwargs):
        from backend.services.report_pdf import render_report_pdf
        report = self.build(*args, **kwargs)
        return self.filename(report), render_report_pdf(report)
