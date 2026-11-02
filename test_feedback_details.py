from copy import deepcopy
from types import SimpleNamespace
import pytest
from backend.services.feedback_service import FeedbackService

class Store:
    def __init__(self, rows): self.rows = rows
    def get_all(self): return deepcopy(self.rows)
    def save(self, row): self.rows.append(deepcopy(row)); return deepcopy(row)

def service(role):
    s = FeedbackService.__new__(FeedbackService)
    form = {'feedback_form_id': 'F', 'title': 'Feedback', 'assessment_id': 'A', 'target_role': role, 'questions': [{'id': 'q1', 'text': 'Assessment', 'required': True}, {'id': 'q2', 'text': 'Application', 'required': True}]}
    s.responses = Store([])
    s.forms = Store([form])
    s._context = lambda *args: 'U'
    s.get_form = lambda fid: form
    s.resolve_form = lambda *args: form
    s.assessments = SimpleNamespace(repository=Store([{'assessment_id':'A','name':'Assessment'}]), tests=SimpleNamespace(repository=Store([])))
    from pathlib import Path
    s.assignments = SimpleNamespace(repository=SimpleNamespace(file_path=Path('backend/data/test_candidates.json')), candidates=SimpleNamespace(list_candidates=lambda: []))
    return s

@pytest.mark.parametrize('role', ['candidate', 'facilitator'])
def test_roundtrip(role, monkeypatch):
    monkeypatch.setattr('backend.services.feedback_service.FacilitatorRepository', lambda path: Store([]))
    s = service(role)
    row = s.submit(role, 'U', 'A', 'F', {'q1':'Good','q2':'Good'}, ratings={'q1':4,'q2':3}, additional_feedback='  More practice  ')
    assert row['average_score'] == 3.5
    assert row['additional_feedback'] == 'More practice'
    pairs = s.response_views()[0]['qa_pairs']
    assert pairs[1]['answer'].endswith('4 / 5')
    assert pairs[-2]['answer'] == '3.5 / 5'
    assert pairs[-1]['answer'] == 'More practice'
    again = s.submit(role, 'U', 'A', 'F', {}, ratings={'q1':1}, additional_feedback='changed')
    assert again == row

@pytest.mark.parametrize('rating', [-1, 6, True, '5', 2.5])
def test_invalid_rating(rating):
    s = service('candidate')
    with pytest.raises(ValueError):
        s.submit('candidate','U','A','F',{'q1':'Good','q2':'Good'},ratings={'q1':rating})
    assert s.responses.rows == []

def test_legacy_missing_metadata(monkeypatch):
    monkeypatch.setattr('backend.services.feedback_service.FacilitatorRepository', lambda path: Store([]))
    s=service('candidate')
    row=s.submit('candidate','U','A','F',{'q1':'Good','q2':'Good'})
    for key in ('ratings','additional_feedback','average_score'): row.pop(key)
    s.responses.rows=[row]
    pairs=s.response_views()[0]['qa_pairs']
    assert pairs[0]['answer']=='Good'
    assert pairs[-2]['answer']=='Not recorded'
    assert pairs[-1]['answer']=='Not recorded'
