import importlib

import pytest

import database.db as db

# NOTE: never import `app` at module level in tests. Importing app.py runs
# init_db()/seed_db() immediately, which would touch the real spendly.db.
# The fixtures below point DB_PATH at a temp file first, then import lazily.


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    module = importlib.import_module("app")
    # app.py's import-time init only runs once per session, so set up
    # a fresh schema and demo user for every test explicitly.
    db.init_db()
    db.seed_db()
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def app(app_module):
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()
