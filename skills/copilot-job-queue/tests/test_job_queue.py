"""Behavior tests for the shared Copilot job queue CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "job_queue.py"


class JobQueueTests(unittest.TestCase):
    """Exercise lifecycle, ownership, and concurrent claim guarantees."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db = Path(self.temporary_directory.name) / "jobs.sqlite3"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_cli(
        self, *arguments: str, check: bool = True
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        command = [sys.executable, str(SCRIPT), "--db", str(self.db), *arguments]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if check and result.returncode != 0:
            self.fail(f"Command failed: {command}\nstdout={result.stdout}\nstderr={result.stderr}")
        output = result.stdout if result.returncode == 0 else result.stderr
        return result, json.loads(output)

    def enqueue(self, title: str = "Test job", priority: int = 0) -> str:
        _, payload = self.run_cli(
            "enqueue",
            "--title",
            title,
            "--instructions",
            "Implement the change and add regression coverage.",
            "--priority",
            str(priority),
        )
        return payload["job"]["id"]

    def test_complete_lifecycle_writes_finished_ledger(self) -> None:
        job_id = self.enqueue()
        _, claimed = self.run_cli("claim", "--worker", "copilot-app")
        self.assertEqual(job_id, claimed["job"]["id"])
        self.assertEqual("claimed", claimed["job"]["status"])

        self.run_cli(
            "set-repo",
            job_id,
            "--worker",
            "copilot-app",
            "--repo",
            r"C:\repos\product",
        )
        _, completed = self.run_cli(
            "finish",
            job_id,
            "--worker",
            "copilot-app",
            "--branch",
            "copilot/test-job",
            "--pr-url",
            "https://github.com/example/product/pull/42",
            "--summary",
            "Implemented and tested the requested change.",
        )

        self.assertEqual("finished", completed["job"]["status"])
        self.assertEqual(job_id, completed["finished_job"]["job_id"])
        self.assertEqual(1, completed["finished_job"]["pr_is_draft"])

        _, discovered = self.run_cli("finished", "--worker", "copilot-app")
        self.assertEqual([job_id], [row["job_id"] for row in discovered["finished_jobs"]])

        _, shown = self.run_cli("show", job_id)
        self.assertEqual(
            ["enqueued", "claimed", "repository_resolved", "finished"],
            [event["event_type"] for event in shown["events"]],
        )

    def test_only_owner_can_finish(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker-a")
        self.run_cli("set-repo", job_id, "--worker", "worker-a", "--repo", "repo-a")
        result, payload = self.run_cli(
            "finish",
            job_id,
            "--worker",
            "worker-b",
            "--branch",
            "branch",
            "--pr-url",
            "https://example.test/pull/1",
            "--summary",
            "Done",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("claimed by worker-a", payload["error"])

    def test_release_makes_job_claimable_again(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker-a")
        _, released = self.run_cli(
            "release",
            job_id,
            "--worker",
            "worker-a",
            "--reason",
            "Wrong repository",
        )
        self.assertEqual("queued", released["job"]["status"])
        self.assertIsNone(released["job"]["claimed_by"])

        _, reclaimed = self.run_cli("claim", "--worker", "worker-b")
        self.assertEqual(job_id, reclaimed["job"]["id"])
        self.assertEqual(2, reclaimed["job"]["attempt_count"])

    def test_priority_controls_claim_order(self) -> None:
        low_id = self.enqueue("Low", priority=1)
        high_id = self.enqueue("High", priority=50)
        _, claimed = self.run_cli("claim", "--worker", "worker")
        self.assertEqual(high_id, claimed["job"]["id"])
        self.assertNotEqual(low_id, claimed["job"]["id"])

    def test_concurrent_claim_assigns_job_once(self) -> None:
        job_id = self.enqueue()

        def claim(worker: str) -> dict[str, Any]:
            return self.run_cli("claim", "--worker", worker)[1]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(claim, ("worker-a", "worker-b")))

        claimed_ids = [payload["job"]["id"] for payload in results if payload["job"]]
        self.assertEqual([job_id], claimed_ids)

    def test_finish_requires_resolved_repository_and_absolute_pr_url(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker")
        result, payload = self.run_cli(
            "finish",
            job_id,
            "--worker",
            "worker",
            "--branch",
            "branch",
            "--pr-url",
            "not-a-url",
            "--summary",
            "Done",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("absolute HTTP(S) URL", payload["error"])

        result, payload = self.run_cli(
            "finish",
            job_id,
            "--worker",
            "worker",
            "--branch",
            "branch",
            "--pr-url",
            "https://example.test/pull/1",
            "--summary",
            "Done",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("no resolved repository", payload["error"])

    def test_block_requires_owner_and_preserves_summary(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker-a")
        result, payload = self.run_cli(
            "block",
            job_id,
            "--worker",
            "worker-b",
            "--summary",
            "Need a repository decision.",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("claimed by worker-a", payload["error"])

        _, blocked = self.run_cli(
            "block",
            job_id,
            "--worker",
            "worker-a",
            "--summary",
            "Both repo-a and repo-b are plausible; need the owning repository.",
        )
        self.assertEqual("blocked", blocked["job"]["status"])
        self.assertIsNone(blocked["job"]["claimed_by"])
        self.assertIn("repo-a", blocked["job"]["summary"])

        _, discovered = self.run_cli("blocked")
        self.assertEqual([job_id], [row["id"] for row in discovered["blocked_jobs"]])

    def test_unblock_enriches_and_requeues_job(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker")
        self.run_cli(
            "block",
            job_id,
            "--worker",
            "worker",
            "--summary",
            "Repository and target branch are missing.",
        )
        _, unblocked = self.run_cli(
            "unblock",
            job_id,
            "--actor",
            "scout-automation",
            "--summary",
            "Work item 123 explicitly names repo-a and main.",
            "--repo-hint",
            "repo-a",
            "--repo",
            r"C:\repos\repo-a",
            "--target-branch",
            "main",
            "--metadata-merge",
            '{"work_item": 123}',
        )
        job = unblocked["job"]
        self.assertEqual("queued", job["status"])
        self.assertEqual("repo-a", job["repo_hint"])
        self.assertEqual(r"C:\repos\repo-a", job["resolved_repo"])
        self.assertEqual("main", job["target_branch"])
        self.assertIn("Unblock context", job["instructions"])
        self.assertEqual(123, json.loads(job["metadata_json"])["work_item"])

        _, shown = self.run_cli("show", job_id)
        self.assertEqual(
            ["enqueued", "claimed", "blocked", "unblocked"],
            [event["event_type"] for event in shown["events"]],
        )

    def test_blocked_job_is_not_claimable_until_unblocked(self) -> None:
        job_id = self.enqueue()
        self.run_cli("claim", "--worker", "worker-a")
        self.run_cli(
            "block",
            job_id,
            "--worker",
            "worker-a",
            "--summary",
            "Need user input.",
        )
        _, empty = self.run_cli("claim", "--worker", "worker-b")
        self.assertIsNone(empty["job"])
        self.run_cli(
            "unblock",
            job_id,
            "--actor",
            "user",
            "--summary",
            "User supplied the missing requirement.",
        )
        _, claimed = self.run_cli("claim", "--worker", "worker-b")
        self.assertEqual(job_id, claimed["job"]["id"])

    def test_migrates_v1_database_without_losing_jobs(self) -> None:
        connection = sqlite3.connect(self.db)
        connection.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version VALUES (1);
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, instructions TEXT NOT NULL,
                repo_hint TEXT, resolved_repo TEXT, target_branch TEXT, source TEXT,
                priority INTEGER NOT NULL DEFAULT 0, metadata_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL CHECK (status IN ('queued', 'claimed', 'finished')),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, claimed_at TEXT,
                claimed_by TEXT, attempt_count INTEGER NOT NULL DEFAULT 0,
                CHECK (
                    (status = 'queued' AND claimed_by IS NULL AND claimed_at IS NULL)
                    OR (status IN ('claimed', 'finished') AND claimed_by IS NOT NULL AND claimed_at IS NOT NULL)
                )
            );
            CREATE TABLE finished_jobs (
                job_id TEXT PRIMARY KEY REFERENCES jobs(id), finished_at TEXT NOT NULL,
                finished_by TEXT NOT NULL, resolved_repo TEXT NOT NULL, branch TEXT NOT NULL,
                pr_url TEXT NOT NULL, pr_is_draft INTEGER NOT NULL DEFAULT 1 CHECK (pr_is_draft = 1),
                summary TEXT NOT NULL
            );
            CREATE TABLE job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES jobs(id),
                event_type TEXT NOT NULL, actor TEXT, occurred_at TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}'
            );
            INSERT INTO jobs(
                id, title, instructions, status, created_at, updated_at
            ) VALUES ('legacy-job', 'Legacy', 'Keep me', 'queued', '2026-01-01Z', '2026-01-01Z');
            INSERT INTO jobs(
                id, title, instructions, status, created_at, updated_at,
                claimed_at, claimed_by, attempt_count
            ) VALUES (
                'legacy-finished', 'Legacy finished', 'Keep summary', 'finished',
                '2026-01-01Z', '2026-01-02Z', '2026-01-02Z', 'legacy-worker', 1
            );
            INSERT INTO finished_jobs(
                job_id, finished_at, finished_by, resolved_repo, branch, pr_url, summary
            ) VALUES (
                'legacy-finished', '2026-01-02Z', 'legacy-worker', 'legacy-repo',
                'legacy-branch', 'https://example.test/pull/1', 'Legacy completion summary'
            );
            """
        )
        connection.commit()
        connection.close()

        _, initialized = self.run_cli("init")
        self.assertEqual(2, initialized["schema_version"])
        _, shown = self.run_cli("show", "legacy-job")
        self.assertEqual("Legacy", shown["job"]["title"])
        self.assertIn("summary", shown["job"])
        _, finished = self.run_cli("show", "legacy-finished")
        self.assertEqual("Legacy completion summary", finished["job"]["summary"])
        self.run_cli("claim", "--worker", "worker")


if __name__ == "__main__":
    unittest.main()
