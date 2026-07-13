#!/usr/bin/env python3
"""Manage a durable SQLite queue shared by Scout and GitHub Copilot."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlparse


SCHEMA_VERSION = 2
STATUSES = ("queued", "claimed", "blocked", "finished")


class QueueError(Exception):
    """Raised when a requested queue transition is invalid."""


def utc_now() -> str:
    """Return a sortable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_db_path() -> Path:
    """Return the shared database path, honoring the environment override."""
    override = os.environ.get("COPILOT_JOB_QUEUE_DB")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "state" / "jobs.sqlite3"


def connect(db_path: Path) -> sqlite3.Connection:
    """Open and initialize the queue database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    initialize_schema(connection)
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create or migrate the queue schema."""
    has_version_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
    ).fetchone()
    if not has_version_table:
        create_schema_v2(connection)
        connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        return

    rows = connection.execute("SELECT version FROM schema_version").fetchall()
    if len(rows) != 1:
        raise QueueError(f"Invalid schema version rows: {[row['version'] for row in rows]}")
    version = rows[0]["version"]
    if version == 1:
        migrate_v1_to_v2(connection)
    elif version != SCHEMA_VERSION:
        raise QueueError(f"Unsupported schema version: {version}")
    create_schema_v2(connection)


def create_schema_v2(connection: sqlite3.Connection) -> None:
    """Create schema version 2 objects that do not already exist."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            instructions TEXT NOT NULL,
            repo_hint TEXT,
            resolved_repo TEXT,
            target_branch TEXT,
            source TEXT,
            priority INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL CHECK (status IN ('queued', 'claimed', 'blocked', 'finished')),
            summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            claimed_at TEXT,
            claimed_by TEXT,
            blocked_at TEXT,
            blocked_by TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            CHECK (
                (status = 'queued' AND claimed_by IS NULL AND claimed_at IS NULL
                    AND blocked_by IS NULL AND blocked_at IS NULL)
                OR (status = 'claimed' AND claimed_by IS NOT NULL AND claimed_at IS NOT NULL
                    AND blocked_by IS NULL AND blocked_at IS NULL)
                OR (status = 'blocked' AND claimed_by IS NULL AND claimed_at IS NULL
                    AND blocked_by IS NOT NULL AND blocked_at IS NOT NULL
                    AND summary IS NOT NULL AND length(trim(summary)) > 0)
                OR (status = 'finished' AND claimed_by IS NOT NULL AND claimed_at IS NOT NULL
                    AND blocked_by IS NULL AND blocked_at IS NULL)
            )
        );

        CREATE TABLE IF NOT EXISTS finished_jobs (
            job_id TEXT PRIMARY KEY REFERENCES jobs(id),
            finished_at TEXT NOT NULL,
            finished_by TEXT NOT NULL,
            resolved_repo TEXT NOT NULL,
            branch TEXT NOT NULL,
            pr_url TEXT NOT NULL,
            pr_is_draft INTEGER NOT NULL DEFAULT 1 CHECK (pr_is_draft = 1),
            summary TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL REFERENCES jobs(id),
            event_type TEXT NOT NULL,
            actor TEXT,
            occurred_at TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_claim_order
            ON jobs(status, priority DESC, created_at, id);
        CREATE INDEX IF NOT EXISTS idx_finished_jobs_time
            ON finished_jobs(finished_at DESC, job_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_blocked_time
            ON jobs(status, blocked_at, id);
        CREATE INDEX IF NOT EXISTS idx_job_events_job
            ON job_events(job_id, id);

        UPDATE jobs
        SET summary = (
            SELECT finished_jobs.summary
            FROM finished_jobs
            WHERE finished_jobs.job_id = jobs.id
        )
        WHERE status = 'finished'
            AND summary IS NULL
            AND EXISTS (
                SELECT 1 FROM finished_jobs WHERE finished_jobs.job_id = jobs.id
            );
        """
    )


def migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
    """Rebuild the jobs table to add blocked-state constraints."""
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.executescript(
            """
            CREATE TABLE jobs_v2 (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                instructions TEXT NOT NULL,
                repo_hint TEXT,
                resolved_repo TEXT,
                target_branch TEXT,
                source TEXT,
                priority INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL CHECK (status IN ('queued', 'claimed', 'blocked', 'finished')),
                summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                claimed_at TEXT,
                claimed_by TEXT,
                blocked_at TEXT,
                blocked_by TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                CHECK (
                    (status = 'queued' AND claimed_by IS NULL AND claimed_at IS NULL
                        AND blocked_by IS NULL AND blocked_at IS NULL)
                    OR (status = 'claimed' AND claimed_by IS NOT NULL AND claimed_at IS NOT NULL
                        AND blocked_by IS NULL AND blocked_at IS NULL)
                    OR (status = 'blocked' AND claimed_by IS NULL AND claimed_at IS NULL
                        AND blocked_by IS NOT NULL AND blocked_at IS NOT NULL
                        AND summary IS NOT NULL AND length(trim(summary)) > 0)
                    OR (status = 'finished' AND claimed_by IS NOT NULL AND claimed_at IS NOT NULL
                        AND blocked_by IS NULL AND blocked_at IS NULL)
                )
            );

            INSERT INTO jobs_v2(
                id, title, instructions, repo_hint, resolved_repo, target_branch, source,
                priority, metadata_json, status, summary, created_at, updated_at,
                claimed_at, claimed_by, blocked_at, blocked_by, attempt_count
            )
            SELECT
                id, title, instructions, repo_hint, resolved_repo, target_branch, source,
                priority, metadata_json, status, NULL, created_at, updated_at,
                claimed_at, claimed_by, NULL, NULL, attempt_count
            FROM jobs;

            DROP TABLE jobs;
            ALTER TABLE jobs_v2 RENAME TO jobs;
            UPDATE schema_version SET version = 2;
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a SQLite row to a JSON-friendly dictionary."""
    return dict(row) if row is not None else None


def parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    """Parse a command-line JSON object."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise QueueError(f"{field_name} must be valid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise QueueError(f"{field_name} must be a JSON object")
    return value


def read_instructions(args: argparse.Namespace) -> str:
    """Read instructions from exactly one supported source."""
    if args.instructions is not None:
        instructions = args.instructions
    else:
        try:
            instructions = Path(args.instructions_file).expanduser().read_text(encoding="utf-8")
        except OSError as error:
            raise QueueError(f"Could not read instructions file: {error}") from error
    instructions = instructions.strip()
    if not instructions:
        raise QueueError("Instructions cannot be empty")
    return instructions


def add_event(
    connection: sqlite3.Connection,
    job_id: str,
    event_type: str,
    actor: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an audit event inside the caller's transaction."""
    connection.execute(
        """
        INSERT INTO job_events(job_id, event_type, actor, occurred_at, details_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (job_id, event_type, actor, utc_now(), json.dumps(details or {}, sort_keys=True)),
    )


def fetch_job(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    """Load one job or fail with a clear message."""
    row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise QueueError(f"Job not found: {job_id}")
    return row


def require_owner(row: sqlite3.Row, worker: str) -> None:
    """Require a claimed job owned by the requesting worker."""
    if row["status"] != "claimed":
        raise QueueError(f"Job {row['id']} is {row['status']}, not claimed")
    if row["claimed_by"] != worker:
        raise QueueError(f"Job {row['id']} is claimed by {row['claimed_by']}, not {worker}")


def command_init(connection: sqlite3.Connection, db_path: Path, _: argparse.Namespace) -> dict[str, Any]:
    """Report initialized database details."""
    return {"database": str(db_path.resolve()), "schema_version": SCHEMA_VERSION}


def command_enqueue(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Insert a new queued job."""
    job_id = str(uuid.uuid4())
    now = utc_now()
    metadata = parse_json_object(args.metadata, "metadata")
    instructions = read_instructions(args)
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """
            INSERT INTO jobs(
                id, title, instructions, repo_hint, target_branch, source, priority,
                metadata_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
            """,
            (
                job_id,
                args.title.strip(),
                instructions,
                args.repo_hint,
                args.target_branch,
                args.source,
                args.priority,
                json.dumps(metadata, sort_keys=True),
                now,
                now,
            ),
        )
        add_event(connection, job_id, "enqueued", args.source, {"priority": args.priority})
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, job_id))}


def command_claim(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Atomically claim one queued job."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        if args.job_id:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ? AND status = 'queued'",
                (args.job_id,),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    "SELECT status, claimed_by FROM jobs WHERE id = ?", (args.job_id,)
                ).fetchone()
                if existing is None:
                    raise QueueError(f"Job not found: {args.job_id}")
                raise QueueError(
                    f"Job {args.job_id} is {existing['status']}"
                    + (f" by {existing['claimed_by']}" if existing["claimed_by"] else "")
                )
        else:
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued'
                ORDER BY priority DESC, created_at, id
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            connection.commit()
            return {"job": None}
        now = utc_now()
        result = connection.execute(
            """
            UPDATE jobs
            SET status = 'claimed', claimed_at = ?, claimed_by = ?,
                attempt_count = attempt_count + 1, updated_at = ?
            WHERE id = ? AND status = 'queued'
            """,
            (now, args.worker, now, row["id"]),
        )
        if result.rowcount != 1:
            raise QueueError(f"Job could not be claimed: {row['id']}")
        add_event(connection, row["id"], "claimed", args.worker)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, row["id"]))}


def command_set_repo(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Record the repository selected for a claimed job."""
    repo = args.repo.strip()
    if not repo:
        raise QueueError("Repository cannot be empty")
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = fetch_job(connection, args.job_id)
        require_owner(row, args.worker)
        now = utc_now()
        connection.execute(
            "UPDATE jobs SET resolved_repo = ?, updated_at = ? WHERE id = ?",
            (repo, now, args.job_id),
        )
        add_event(connection, args.job_id, "repository_resolved", args.worker, {"repo": repo})
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, args.job_id))}


def command_release(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Return a claimed job to the queue."""
    reason = args.reason.strip()
    if not reason:
        raise QueueError("Release reason cannot be empty")
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = fetch_job(connection, args.job_id)
        require_owner(row, args.worker)
        now = utc_now()
        connection.execute(
            """
            UPDATE jobs
            SET status = 'queued', claimed_at = NULL, claimed_by = NULL,
                resolved_repo = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, args.job_id),
        )
        add_event(connection, args.job_id, "released", args.worker, {"reason": reason})
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, args.job_id))}


def command_block(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Mark claimed work as blocked with a durable summary."""
    summary = args.summary.strip()
    if not summary:
        raise QueueError("Blocked summary cannot be empty")
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = fetch_job(connection, args.job_id)
        require_owner(row, args.worker)
        now = utc_now()
        connection.execute(
            """
            UPDATE jobs
            SET status = 'blocked', summary = ?, blocked_at = ?, blocked_by = ?,
                claimed_at = NULL, claimed_by = NULL, updated_at = ?
            WHERE id = ?
            """,
            (summary, now, args.worker, now, args.job_id),
        )
        add_event(connection, args.job_id, "blocked", args.worker, {"summary": summary})
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, args.job_id))}


def merge_metadata(existing_json: str, raw_update: str | None) -> str:
    """Merge explicit metadata corrections into existing metadata."""
    existing = parse_json_object(existing_json, "stored metadata")
    if raw_update is not None:
        existing.update(parse_json_object(raw_update, "metadata merge"))
    return json.dumps(existing, sort_keys=True)


def command_unblock(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Enrich a blocked job and atomically return it to the queue."""
    summary = args.summary.strip()
    if not summary:
        raise QueueError("Unblock summary cannot be empty")
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = fetch_job(connection, args.job_id)
        if row["status"] != "blocked":
            raise QueueError(f"Job {args.job_id} is {row['status']}, not blocked")
        instructions = (
            f"{row['instructions'].rstrip()}\n\n"
            f"Unblock context ({utc_now()} by {args.actor}):\n{summary}"
        )
        now = utc_now()
        connection.execute(
            """
            UPDATE jobs
            SET status = 'queued', instructions = ?, summary = ?,
                repo_hint = COALESCE(?, repo_hint),
                resolved_repo = COALESCE(?, resolved_repo),
                target_branch = COALESCE(?, target_branch),
                metadata_json = ?, blocked_at = NULL, blocked_by = NULL,
                claimed_at = NULL, claimed_by = NULL, updated_at = ?
            WHERE id = ?
            """,
            (
                instructions,
                summary,
                args.repo_hint,
                args.repo,
                args.target_branch,
                merge_metadata(row["metadata_json"], args.metadata_merge),
                now,
                args.job_id,
            ),
        )
        details = {
            "summary": summary,
            "repo_hint": args.repo_hint,
            "resolved_repo": args.repo,
            "target_branch": args.target_branch,
        }
        add_event(connection, args.job_id, "unblocked", args.actor, details)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {"job": row_dict(fetch_job(connection, args.job_id))}


def validate_pr_url(raw_url: str) -> str:
    """Require an absolute HTTP(S) pull-request URL."""
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise QueueError("PR URL must be an absolute HTTP(S) URL")
    return value


def command_finish(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Atomically record successful completion in both lifecycle tables."""
    branch = args.branch.strip()
    summary = args.summary.strip()
    if not branch:
        raise QueueError("Branch cannot be empty")
    if not summary:
        raise QueueError("Summary cannot be empty")
    pr_url = validate_pr_url(args.pr_url)
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = fetch_job(connection, args.job_id)
        require_owner(row, args.worker)
        if not row["resolved_repo"]:
            raise QueueError(f"Job {args.job_id} has no resolved repository")
        now = utc_now()
        connection.execute(
            """
            INSERT INTO finished_jobs(
                job_id, finished_at, finished_by, resolved_repo, branch, pr_url, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                args.job_id,
                now,
                args.worker,
                row["resolved_repo"],
                branch,
                pr_url,
                summary,
            ),
        )
        connection.execute(
            "UPDATE jobs SET status = 'finished', summary = ?, updated_at = ? WHERE id = ?",
            (summary, now, args.job_id),
        )
        add_event(
            connection,
            args.job_id,
            "finished",
            args.worker,
            {"branch": branch, "pr_url": pr_url},
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finished = connection.execute(
        "SELECT * FROM finished_jobs WHERE job_id = ?", (args.job_id,)
    ).fetchone()
    return {
        "job": row_dict(fetch_job(connection, args.job_id)),
        "finished_job": row_dict(finished),
    }


def command_list(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """List jobs in deterministic queue order."""
    if args.status == "all":
        rows = connection.execute(
            """
            SELECT * FROM jobs
            ORDER BY
                CASE status WHEN 'queued' THEN 0 WHEN 'claimed' THEN 1
                    WHEN 'blocked' THEN 2 ELSE 3 END,
                priority DESC, created_at, id
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT * FROM jobs WHERE status = ?
            ORDER BY priority DESC, created_at, id
            LIMIT ?
            """,
            (args.status, args.limit),
        ).fetchall()
    return {"jobs": [dict(row) for row in rows]}


def command_show(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Show a job, completion record, and audit events."""
    job = fetch_job(connection, args.job_id)
    finished = connection.execute(
        "SELECT * FROM finished_jobs WHERE job_id = ?", (args.job_id,)
    ).fetchone()
    events = connection.execute(
        "SELECT * FROM job_events WHERE job_id = ? ORDER BY id", (args.job_id,)
    ).fetchall()
    return {
        "job": dict(job),
        "finished_job": row_dict(finished),
        "events": [dict(row) for row in events],
    }


def command_finished(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Discover finished jobs, newest first."""
    clauses: list[str] = []
    values: list[Any] = []
    if args.since:
        clauses.append("f.finished_at >= ?")
        values.append(args.since)
    if args.worker:
        clauses.append("f.finished_by = ?")
        values.append(args.worker)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(args.limit)
    rows = connection.execute(
        f"""
        SELECT
            f.*, j.title, j.instructions, j.target_branch, j.source,
            j.priority, j.metadata_json, j.created_at
        FROM finished_jobs AS f
        JOIN jobs AS j ON j.id = f.job_id
        {where}
        ORDER BY f.finished_at DESC, f.job_id
        LIMIT ?
        """,
        values,
    ).fetchall()
    return {"finished_jobs": [dict(row) for row in rows]}


def command_blocked(connection: sqlite3.Connection, _: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Discover blocked jobs that may need enrichment or user input."""
    clauses = ["status = 'blocked'"]
    values: list[Any] = []
    if args.since:
        clauses.append("blocked_at >= ?")
        values.append(args.since)
    values.append(args.limit)
    rows = connection.execute(
        f"""
        SELECT * FROM jobs
        WHERE {' AND '.join(clauses)}
        ORDER BY blocked_at, id
        LIMIT ?
        """,
        values,
    ).fetchall()
    return {"blocked_jobs": [dict(row) for row in rows]}


def add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Define the stable command-line interface."""
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize and report the database")
    init_parser.set_defaults(handler=command_init)

    enqueue_parser = subparsers.add_parser("enqueue", help="Submit a queued job")
    enqueue_parser.add_argument("--title", required=True)
    instructions = enqueue_parser.add_mutually_exclusive_group(required=True)
    instructions.add_argument("--instructions")
    instructions.add_argument("--instructions-file")
    enqueue_parser.add_argument("--repo-hint")
    enqueue_parser.add_argument("--target-branch")
    enqueue_parser.add_argument("--source", default="scout")
    enqueue_parser.add_argument("--priority", type=int, default=0)
    enqueue_parser.add_argument("--metadata", default="{}")
    enqueue_parser.set_defaults(handler=command_enqueue)

    claim_parser = subparsers.add_parser("claim", help="Atomically claim a queued job")
    claim_parser.add_argument("--worker", required=True)
    claim_parser.add_argument("--job-id")
    claim_parser.set_defaults(handler=command_claim)

    repo_parser = subparsers.add_parser("set-repo", help="Record the resolved repository")
    repo_parser.add_argument("job_id")
    repo_parser.add_argument("--worker", required=True)
    repo_parser.add_argument("--repo", required=True)
    repo_parser.set_defaults(handler=command_set_repo)

    release_parser = subparsers.add_parser("release", help="Return a claimed job to the queue")
    release_parser.add_argument("job_id")
    release_parser.add_argument("--worker", required=True)
    release_parser.add_argument("--reason", required=True)
    release_parser.set_defaults(handler=command_release)

    block_parser = subparsers.add_parser("block", help="Record missing information or a decision")
    block_parser.add_argument("job_id")
    block_parser.add_argument("--worker", required=True)
    block_parser.add_argument("--summary", required=True)
    block_parser.set_defaults(handler=command_block)

    unblock_parser = subparsers.add_parser("unblock", help="Enrich and requeue blocked work")
    unblock_parser.add_argument("job_id")
    unblock_parser.add_argument("--actor", required=True)
    unblock_parser.add_argument("--summary", required=True)
    unblock_parser.add_argument("--repo-hint")
    unblock_parser.add_argument("--repo")
    unblock_parser.add_argument("--target-branch")
    unblock_parser.add_argument("--metadata-merge")
    unblock_parser.set_defaults(handler=command_unblock)

    finish_parser = subparsers.add_parser("finish", help="Record a pushed branch and draft PR")
    finish_parser.add_argument("job_id")
    finish_parser.add_argument("--worker", required=True)
    finish_parser.add_argument("--branch", required=True)
    finish_parser.add_argument("--pr-url", required=True)
    finish_parser.add_argument("--summary", required=True)
    finish_parser.set_defaults(handler=command_finish)

    list_parser = subparsers.add_parser("list", help="List jobs")
    list_parser.add_argument("--status", choices=(*STATUSES, "all"), default="queued")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.set_defaults(handler=command_list)

    show_parser = subparsers.add_parser("show", help="Show one job and its history")
    show_parser.add_argument("job_id")
    show_parser.set_defaults(handler=command_show)

    finished_parser = subparsers.add_parser("finished", help="Discover finished jobs")
    finished_parser.add_argument("--since")
    finished_parser.add_argument("--worker")
    finished_parser.add_argument("--limit", type=int, default=100)
    finished_parser.set_defaults(handler=command_finished)

    blocked_parser = subparsers.add_parser("blocked", help="Discover blocked jobs")
    blocked_parser.add_argument("--since")
    blocked_parser.add_argument("--limit", type=int, default=100)
    blocked_parser.set_defaults(handler=command_blocked)


def emit(payload: dict[str, Any], stream: Any = sys.stdout) -> None:
    """Write one machine-readable response."""
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


def fail(error: Exception) -> NoReturn:
    """Emit a structured error and terminate."""
    emit({"error": str(error), "type": error.__class__.__name__}, sys.stderr)
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    """Run the queue command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=default_db_path())
    add_parser_arguments(parser)
    args = parser.parse_args(argv)
    if hasattr(args, "limit") and args.limit < 1:
        parser.error("--limit must be at least 1")
    if hasattr(args, "title") and not args.title.strip():
        parser.error("--title cannot be empty")
    try:
        with connect(args.db) as connection:
            payload = args.handler(connection, args.db, args)
        emit(payload)
        return 0
    except (QueueError, sqlite3.Error) as error:
        fail(error)


if __name__ == "__main__":
    raise SystemExit(main())
