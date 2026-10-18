"""SQLite persistence and seed data for the RFP evaluation project."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("rfp_evaluation.db")
SEED_CRITERIA = [
    ("Technical Capability", "Architecture, integrations, scalability, and technical fit.", 30.0, 10.0),
    ("Implementation Plan", "Timeline, milestones, staffing, and risk plan.", 20.0, 10.0),
    ("Commercial Value", "Pricing clarity, total cost, and assumptions.", 20.0, 10.0),
    ("Security & Compliance", "Controls, certifications, privacy, and auditability.", 20.0, 10.0),
    ("Support & Experience", "Support model, similar projects, and references.", 10.0, 10.0),
]


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                weight REAL NOT NULL CHECK(weight >= 0 AND weight <= 100),
                max_score REAL NOT NULL CHECK(max_score > 0),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS rfp_runs (
                rfp_run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_id TEXT
            );
            CREATE TABLE IF NOT EXISTS supplier_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id) ON DELETE CASCADE,
                supplier_name TEXT NOT NULL,
                submission_date TEXT NOT NULL,
                experience_rating REAL NOT NULL,
                absolute_score REAL NOT NULL,
                ppi REAL NOT NULL,
                final_rank INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                UNIQUE(rfp_run_id, supplier_name)
            );
            CREATE TABLE IF NOT EXISTS criterion_results (
                result_id INTEGER NOT NULL REFERENCES supplier_results(result_id) ON DELETE CASCADE,
                criterion_id INTEGER NOT NULL REFERENCES evaluation_criteria(criterion_id),
                score REAL NOT NULL,
                max_score REAL NOT NULL,
                weight REAL NOT NULL,
                benchmark REAL NOT NULL,
                gap REAL NOT NULL,
                relative_performance REAL NOT NULL,
                justification TEXT NOT NULL,
                evidence TEXT NOT NULL,
                PRIMARY KEY(result_id, criterion_id)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_results_run_rank
                ON supplier_results(rfp_run_id, final_rank);
        """)
        run_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(rfp_runs)")
        }
        if "owner_id" not in run_columns:
            connection.execute("ALTER TABLE rfp_runs ADD COLUMN owner_id TEXT")
        count = connection.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if count == 0:
            connection.executemany(
                "INSERT INTO evaluation_criteria(name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, 1)",
                SEED_CRITERIA,
            )


def get_criteria(db_path: Path | str = DB_PATH, active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM evaluation_criteria" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY criterion_id"
    with connect(db_path) as connection:
        return [dict(row) for row in connection.execute(query).fetchall()]


def update_criteria(criteria: list[dict[str, Any]], db_path: Path | str = DB_PATH) -> None:
    active = [criterion for criterion in criteria if criterion["is_active"]]
    if active and abs(sum(float(item["weight"]) for item in active) - 100.0) > 0.01:
        raise ValueError("Active criterion weights must total exactly 100%.")
    with connect(db_path) as connection:
        for item in criteria:
            connection.execute(
                "UPDATE evaluation_criteria SET description=?, weight=?, max_score=?, is_active=? WHERE criterion_id=?",
                (item["description"], item["weight"], item["max_score"], int(item["is_active"]), item["criterion_id"]),
            )


def create_run(owner_id: str, db_path: Path | str = DB_PATH) -> str:
    owner_id = owner_id.strip()
    if not owner_id:
        raise ValueError("An authenticated owner ID is required to create a run.")
    run_id = str(uuid.uuid4())
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO rfp_runs(rfp_run_id, created_at, status, owner_id) VALUES (?, ?, ?, ?)",
            (run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"), "running", owner_id),
        )
    return run_id


def persist_results(
    run_id: str,
    owner_id: str,
    results: list[dict[str, Any]],
    db_path: Path | str = DB_PATH,
) -> None:
    """Persist leaderboard and scorecards together; mark the run complete atomically."""
    with connect(db_path) as connection:
        with connection:
            owner = connection.execute(
                "SELECT 1 FROM rfp_runs WHERE rfp_run_id=? AND owner_id=?",
                (run_id, owner_id.strip()),
            ).fetchone()
            if owner is None:
                raise ValueError("Run not found or not owned by the authenticated user.")
            for supplier in results:
                result_json = json.dumps(supplier, ensure_ascii=False)
                cursor = connection.execute(
                    """INSERT INTO supplier_results
                    (rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, supplier["supplier_name"], supplier["submission_date"], supplier["experience_rating"],
                     supplier["absolute_score"], supplier["ppi"], supplier["final_rank"], result_json),
                )
                for item in supplier["criteria"]:
                    connection.execute(
                        """INSERT INTO criterion_results
                        (result_id, criterion_id, score, max_score, weight, benchmark, gap,
                         relative_performance, justification, evidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (cursor.lastrowid, item["criterion_id"], item["score"], item["max_score"], item["weight"],
                         item["benchmark"], item["gap"], item["relative_performance"], item["justification"], item["evidence"]),
                    )
            connection.execute(
                "UPDATE rfp_runs SET status='complete' WHERE rfp_run_id=? AND owner_id=?",
                (run_id, owner_id.strip()),
            )


def mark_run_failed(run_id: str, owner_id: str, db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE rfp_runs SET status='failed' WHERE rfp_run_id=? AND owner_id=?",
            (run_id, owner_id.strip()),
        )


def get_run_ids(owner_id: str, db_path: Path | str = DB_PATH) -> list[str]:
    with connect(db_path) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT rfp_run_id FROM rfp_runs WHERE status='complete' AND owner_id=? ORDER BY created_at DESC",
                (owner_id.strip(),),
            )
        ]


def get_run_results(
    run_id: str,
    owner_id: str,
    db_path: Path | str = DB_PATH,
) -> list[dict[str, Any]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """SELECT sr.result_json
            FROM supplier_results sr
            JOIN rfp_runs r ON r.rfp_run_id = sr.rfp_run_id
            WHERE sr.rfp_run_id=? AND r.owner_id=?
            ORDER BY sr.final_rank""",
            (run_id, owner_id.strip()),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]
