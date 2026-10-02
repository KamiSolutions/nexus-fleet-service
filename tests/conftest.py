"""
Point every test run at a fresh, isolated on-disk SQLite file — same
reasoning as nexus-financials-service's `tests/conftest.py` (see that
file's full docstring for why a real file, not `:memory:`):
`test_fleet.py` and `test_fleet_writes.py` each instantiate their own
`TestClient(app)`, each running on its own event loop, and an in-memory
SQLite DB is scoped to the single connection/loop that created it.

Must be set before any `app.*` module is imported — pytest loads every
`conftest.py` in a directory before collecting that directory's test
modules.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "nexus_fleet_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"


@pytest.fixture(scope="session", autouse=True)
def _trigger_lifespan():
    """
    `app/main.py` now bootstraps the database (create tables) from a
    FastAPI lifespan handler instead of at import time — see that file's
    docstring for why. Something has to actually enter that lifespan
    before any test runs; every test file in this suite still uses a
    plain module-level `client = TestClient(app)` (unchanged, no edits
    needed there) because this fixture's own `with TestClient(app):`
    triggers the lifespan once, against the same shared `engine`/SQLite
    file every other `TestClient` instance in this process also uses.
    Session-scoped + autouse so it always runs first, exactly once.
    """
    from app.main import app

    with TestClient(app):
        yield
