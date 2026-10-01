import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.repositories.assessment_repository import AssessmentRepository
from backend.repositories.test_repository import TestRepository
from backend.services.assessment_service import AssessmentService
from backend.services.test_service import TestService

class CatalogPerformanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.assessments = AssessmentRepository(Path(temp.name) / 'assessments.json')
        self.tests = TestRepository(Path(temp.name) / 'tests.json')
        self.assessments.save_all([{'assessment_id': str(i), 'name': str(i)} for i in range(20)])
        self.tests.save_all([{'test_id': f'{i}-{j}', 'assessment_id': str(i), 'test_name': str(j), 'position': 2-j} for i in range(20) for j in range(3)])
        self.service = TestService(self.tests, self.assessments)

    def test_assessment_load_reads_each_file_once_and_preserves_order(self):
        with patch.object(self.tests, 'get_all', wraps=self.tests.get_all) as tests, patch.object(self.assessments, 'get_all', wraps=self.assessments.get_all) as assessments:
            rows = AssessmentService(self.assessments, self.service).load_assessments()
            self.assertEqual(len(rows), 20)
            self.assertEqual(rows[0]['tests'], ['2', '1', '0'])
            self.assertEqual(rows[0]['test_ids']['0'], '0-0')
            self.assertEqual(tests.call_count, 1)
            self.assertEqual(assessments.call_count, 1)

    def test_test_listing_reads_each_file_once_and_preserves_defaults(self):
        with patch.object(self.tests, 'get_all', wraps=self.tests.get_all) as tests, patch.object(self.assessments, 'get_all', wraps=self.assessments.get_all) as assessments:
            rows = self.service.list_tests()
            self.assertEqual(len(rows), 60)
            self.assertEqual(rows[0]['status'], 'Draft')
            self.assertEqual(tests.call_count, 1)
            self.assertEqual(assessments.call_count, 1)

    def test_scoping_and_fresh_reads(self):
        self.assertEqual({r['assessment_id'] for r in self.service.list_tests('1')}, {'1'})
        self.assessments.save_all([])
        with self.assertRaisesRegex(ValueError, 'Assessment not found'):
            self.service.list_tests('1')
        with self.assertRaisesRegex(ValueError, 'Assessment not found'):
            self.service.list_tests()

    def test_invalid_assessment_rejected(self):
        for identity in ('', ' ', 1):
            with self.assertRaisesRegex(ValueError, 'Assessment ID is required'):
                self.service.list_tests(identity)
