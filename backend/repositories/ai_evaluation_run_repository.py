from copy import deepcopy
from pathlib import Path
from backend.repositories.json_repository import JSONRepository


class AIEvaluationRunRepository:
    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else Path(__file__).resolve().parents[1] / 'data' / 'ai_evaluation_runs.json'

    def get_all(self):
        rows = JSONRepository(self.file_path).get_all()
        ids = [r.get('run_id') for r in rows]
        if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Invalid evaluation run identities; storage was not changed.')
        for row in rows:
            if (row.get('status') not in {'idle','running','stop_requested','paused','completed','failed','restarting','abandoned'}
                    or not isinstance(row.get('questions'), list) or not row['questions']
                    or not isinstance(row.get('candidate_ids'), list)
                    or not isinstance(row.get('assessment_name'), str) or not isinstance(row.get('test_name'), str)):
                raise ValueError('Invalid evaluation run data; storage was not changed.')
            if any(not isinstance(q, dict) or q.get('status') not in {'pending','evaluating','completed','failed'}
                   or not isinstance(q.get('record'), dict) or not q.get('pair_id') for q in row['questions']):
                raise ValueError('Invalid evaluation question data; storage was not changed.')
        return rows

    def get(self, run_id):
        record = next((r for r in self.get_all() if r['run_id'] == run_id), None)
        if record is None:
            raise ValueError('Evaluation run does not exist.')
        return deepcopy(record)

    def save(self, record):
        rows = self.get_all()
        rows = [r for r in rows if r['run_id'] != record['run_id']] + [deepcopy(record)]
        JSONRepository(self.file_path).save_all(rows)
        return deepcopy(record)

    def save_many(self, records):
        existing = self.get_all()
        ids = {r['run_id'] for r in records}
        JSONRepository(self.file_path).save_all([r for r in existing if r['run_id'] not in ids] + deepcopy(records))
