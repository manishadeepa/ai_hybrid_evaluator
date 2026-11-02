import importlib.util
import json
from pathlib import Path
import pytest

from backend import data_paths as dp

@pytest.fixture
def project(tmp_path,monkeypatch):
    monkeypatch.setattr(dp,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(dp,'DEFAULT_DATA_DIR',tmp_path/'backend/data')
    monkeypatch.setattr(dp,'DATA_LOCATION_FILE',tmp_path/'backend/data_location.json')
    return tmp_path

def write(root,folder,name,value):
    p=root/folder/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value),encoding='utf-8')
    return p

def test_formatting_and_repeat(project):
    src=write(project,'ai_hybrid_evaluator/data','assessment_weightages.json',{'A':{'T':100}})
    dst=write(project,'backend/data',src.name,{'A':{'T':100}})
    src.write_text('{"A": {"T": 100}}\n',encoding='utf-8-sig')
    before=dst.read_bytes()
    assert dp.get_active_data_dir()==dst.parent
    assert dst.read_bytes()==before
    dst.write_text('{"A":{"T":90}}')
    for _ in range(3): assert dp.get_active_data_dir()==dst.parent
    assert json.loads(dst.read_text())['A']['T']==90
    assert len(list((project/'backend/migration_backups').glob('*/legacy/*.json')))==1

def test_union_and_qfd3(project):
    write(project,'ai_hybrid_evaluator/data','assessment_weightages.json',{'HoQ':{'T1':80,'T2':20}})
    dst=write(project,'backend/data','assessment_weightages.json',{'HoQ':{'T1':80},'QFD 3':{'Formative 1':100}})
    dp.get_active_data_dir()
    assert json.loads(dst.read_text())=={'HoQ':{'T1':80,'T2':20},'QFD 3':{'Formative 1':100}}
    saved=json.loads(dst.read_text()); saved['QFD 3']['Formative 1']=95
    dst.write_text(json.dumps(saved))
    dp.get_active_data_dir()
    assert json.loads(dst.read_text())['QFD 3']['Formative 1']==95

def test_conflict_preserves_all_and_backs_up(project):
    src=write(project,'ai_hybrid_evaluator/data','assessment_weightages.json',{'QFD 3':{'Formative 1':80}})
    dst=write(project,'backend/data',src.name,{'QFD 3':{'Formative 1':100}})
    before=[p.read_bytes() for p in (src,dst)]
    with pytest.raises(ValueError,match=r'/QFD 3/Formative 1: legacy=80, backend=100'):
        dp.get_active_data_dir()
    assert [p.read_bytes() for p in (src,dst)]==before
    assert not (project/'backend/legacy_state_migration.json').exists()
    assert len(list((project/'backend/migration_backups').glob('*/*/*.json')))==2

@pytest.mark.parametrize('name',dp.LEGACY_STATE_FILES)
def test_other_files_and_restart(project,name):
    write(project,'ai_hybrid_evaluator/data',name,{'A':{'T':1}})
    dst=write(project,'backend/data',name,{'B':{'T':2}})
    dp.get_active_data_dir()
    assert json.loads(dst.read_text())=={'A':{'T':1},'B':{'T':2}}
    # Simulate another process loading fresh module state by calling resolution again.
    dp.get_active_data_dir()
    assert len(json.loads((project/'backend/legacy_state_migration.json').read_text())['files'])==1

def test_copy_no_overwrite_still_protected(project):
    src=write(project,'ai_hybrid_evaluator/data','x.json',{'a':1})
    dst=write(project,'backend/data','x.json',{'a':2})
    with pytest.raises(ValueError,match='Conflicting data file'): dp.copy_file_no_overwrite(src,dst)

def test_concurrent_resolution(project):
    from concurrent.futures import ThreadPoolExecutor
    write(project,'ai_hybrid_evaluator/data','assessment_weightages.json',{'A':{'T':100}})
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(p==dp.DEFAULT_DATA_DIR for p in pool.map(lambda _:dp.get_active_data_dir(),range(8)))
    assert len(list((project/'backend/migration_backups').glob('*/legacy/*.json')))==1
