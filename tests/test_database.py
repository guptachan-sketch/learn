import sqlite3

import pytest

from database import (
    create_run,
    get_run_ids,
    get_run_results,
    initialize_database,
    persist_results,
)


def test_initialize_database_migrates_existing_run_table(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE rfp_runs (rfp_run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL)"
        )

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(rfp_runs)")}
        criteria_count = connection.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
    assert "owner_id" in columns
    assert criteria_count == 5


def test_run_history_is_private_to_authenticated_owner(tmp_path):
    db_path = tmp_path / "private-runs.db"
    initialize_database(db_path)
    owner_run = create_run("oidc-user-a", db_path)
    other_run = create_run("oidc-user-b", db_path)
    result = {
        "supplier_name": "Supplier A",
        "submission_date": "2026-10-18",
        "experience_rating": 4,
        "absolute_score": 80,
        "ppi": 100,
        "final_rank": 1,
        "criteria": [],
    }

    persist_results(owner_run, "oidc-user-a", [result], db_path)
    persist_results(other_run, "oidc-user-b", [result], db_path)

    assert get_run_ids("oidc-user-a", db_path) == [owner_run]
    assert get_run_ids("oidc-user-b", db_path) == [other_run]
    assert get_run_results(owner_run, "oidc-user-a", db_path) == [result]
    assert get_run_results(owner_run, "oidc-user-b", db_path) == []


def test_owner_cannot_persist_another_users_run(tmp_path):
    db_path = tmp_path / "private-runs.db"
    initialize_database(db_path)
    run_id = create_run("oidc-user-a", db_path)

    with pytest.raises(ValueError, match="not owned"):
        persist_results(run_id, "oidc-user-b", [], db_path)

    with sqlite3.connect(db_path) as connection:
        status = connection.execute(
            "SELECT status FROM rfp_runs WHERE rfp_run_id=?", (run_id,)
        ).fetchone()[0]
    assert status == "running"


def test_create_run_requires_owner_id(tmp_path):
    db_path = tmp_path / "private-runs.db"
    initialize_database(db_path)

    with pytest.raises(ValueError, match="owner ID"):
        create_run(" ", db_path)
