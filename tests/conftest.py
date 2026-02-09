import os
import tempfile
import shutil
import pytest

@pytest.fixture(scope="session")
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture
def set_db_path(temp_dir, monkeypatch):
    db_path = os.path.join(temp_dir, "reflections_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    monkeypatch.setenv("REFLECTIONS_DB_PATH", db_path)
    yield db_path
