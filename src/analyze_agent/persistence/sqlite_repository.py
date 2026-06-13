"""SQLite implementation of immutable requirement revision storage."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from analyze_agent.domain.models import RequirementChange, SearchFeedback
from analyze_agent.persistence.errors import (
    RequirementNotFoundError,
    RevisionConflictError,
)
from analyze_agent.persistence.models import RequirementRevision

_FEEDBACK_ADAPTER = TypeAdapter(list[SearchFeedback])
_CHANGES_ADAPTER = TypeAdapter(list[RequirementChange])


class SQLiteRequirementRepository:
    """Store requirements as immutable, monotonically numbered revisions."""

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self._database_path = Path(database_path)
        self._timeout_seconds = timeout_seconds

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS requirements (
                    requirement_id TEXT PRIMARY KEY,
                    initial_requirement TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id TEXT PRIMARY KEY,
                    requirement_id TEXT NOT NULL,
                    revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
                    full_requirement TEXT NOT NULL,
                    supplemental_information TEXT,
                    analyzed_requirement_json TEXT,
                    changes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (requirement_id, revision_number),
                    FOREIGN KEY (requirement_id)
                        REFERENCES requirements(requirement_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (revision_id)
                        REFERENCES revisions(revision_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS output_snapshots (
                    revision_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (revision_id)
                        REFERENCES revisions(revision_id)
                        ON DELETE CASCADE
                );
                """
            )

    def create_requirement(
        self,
        *,
        full_requirement: str,
        analyzed_requirement: Mapping[str, Any] | None = None,
        feedback: Sequence[SearchFeedback] = (),
        output_snapshot: Mapping[str, Any] | None = None,
    ) -> RequirementRevision:
        requirement_id = uuid4()
        revision_id = uuid4()
        created_at = _utc_now()

        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO requirements (
                    requirement_id, initial_requirement, created_at
                ) VALUES (?, ?, ?)
                """,
                (str(requirement_id), full_requirement, created_at),
            )
            self._insert_revision(
                connection,
                requirement_id=requirement_id,
                revision_id=revision_id,
                revision_number=1,
                full_requirement=full_requirement,
                supplemental_information=None,
                analyzed_requirement=analyzed_requirement,
                changes=(),
                feedback=feedback,
                output_snapshot=output_snapshot,
                created_at=created_at,
            )
            return self._get_revision(connection, revision_id)

    def get_latest_revision(self, requirement_id: UUID) -> RequirementRevision:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT revision_id
                FROM revisions
                WHERE requirement_id = ?
                ORDER BY revision_number DESC
                LIMIT 1
                """,
                (str(requirement_id),),
            ).fetchone()
            if row is None:
                raise RequirementNotFoundError(requirement_id)
            return self._get_revision(connection, UUID(row["revision_id"]))

    def list_revisions(self, requirement_id: UUID) -> list[RequirementRevision]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT revision_id
                FROM revisions
                WHERE requirement_id = ?
                ORDER BY revision_number ASC
                """,
                (str(requirement_id),),
            ).fetchall()
            if not rows:
                raise RequirementNotFoundError(requirement_id)
            return [
                self._get_revision(connection, UUID(row["revision_id"]))
                for row in rows
            ]

    def append_revision(
        self,
        *,
        requirement_id: UUID,
        expected_base_revision_number: int,
        full_requirement: str,
        supplemental_information: str | None,
        analyzed_requirement: Mapping[str, Any] | None = None,
        changes: Sequence[RequirementChange] = (),
        feedback: Sequence[SearchFeedback] = (),
        output_snapshot: Mapping[str, Any] | None = None,
    ) -> RequirementRevision:
        revision_id = uuid4()
        created_at = _utc_now()

        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT revision_number
                FROM revisions
                WHERE requirement_id = ?
                ORDER BY revision_number DESC
                LIMIT 1
                """,
                (str(requirement_id),),
            ).fetchone()
            if row is None:
                raise RequirementNotFoundError(requirement_id)

            actual_revision_number = int(row["revision_number"])
            if actual_revision_number != expected_base_revision_number:
                raise RevisionConflictError(
                    requirement_id=requirement_id,
                    expected_revision_number=expected_base_revision_number,
                    actual_revision_number=actual_revision_number,
                )

            self._insert_revision(
                connection,
                requirement_id=requirement_id,
                revision_id=revision_id,
                revision_number=actual_revision_number + 1,
                full_requirement=full_requirement,
                supplemental_information=supplemental_information,
                analyzed_requirement=analyzed_requirement,
                changes=changes,
                feedback=feedback,
                output_snapshot=output_snapshot,
                created_at=created_at,
            )
            return self._get_revision(connection, revision_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _transaction(self) -> _SQLiteTransaction:
        return _SQLiteTransaction(self._connect())

    def _insert_revision(
        self,
        connection: sqlite3.Connection,
        *,
        requirement_id: UUID,
        revision_id: UUID,
        revision_number: int,
        full_requirement: str,
        supplemental_information: str | None,
        analyzed_requirement: Mapping[str, Any] | None,
        changes: Sequence[RequirementChange],
        feedback: Sequence[SearchFeedback],
        output_snapshot: Mapping[str, Any] | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO revisions (
                revision_id,
                requirement_id,
                revision_number,
                full_requirement,
                supplemental_information,
                analyzed_requirement_json,
                changes_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(revision_id),
                str(requirement_id),
                revision_number,
                full_requirement,
                supplemental_information,
                _json_dump(analyzed_requirement)
                if analyzed_requirement is not None
                else None,
                _json_dump(
                    _CHANGES_ADAPTER.dump_python(list(changes), mode="json")
                ),
                created_at,
            ),
        )
        for item in feedback:
            connection.execute(
                """
                INSERT INTO feedback (revision_id, payload_json)
                VALUES (?, ?)
                """,
                (str(revision_id), _json_dump(item.model_dump(mode="json"))),
            )
        if output_snapshot is not None:
            connection.execute(
                """
                INSERT INTO output_snapshots (revision_id, payload_json)
                VALUES (?, ?)
                """,
                (str(revision_id), _json_dump(output_snapshot)),
            )

    def _get_revision(
        self,
        connection: sqlite3.Connection,
        revision_id: UUID,
    ) -> RequirementRevision:
        row = connection.execute(
            """
            SELECT
                revision_id,
                requirement_id,
                revision_number,
                full_requirement,
                supplemental_information,
                analyzed_requirement_json,
                changes_json,
                created_at
            FROM revisions
            WHERE revision_id = ?
            """,
            (str(revision_id),),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Revision {revision_id} disappeared during transaction.")

        feedback_rows = connection.execute(
            """
            SELECT payload_json
            FROM feedback
            WHERE revision_id = ?
            ORDER BY feedback_id ASC
            """,
            (str(revision_id),),
        ).fetchall()
        snapshot_row = connection.execute(
            """
            SELECT payload_json
            FROM output_snapshots
            WHERE revision_id = ?
            """,
            (str(revision_id),),
        ).fetchone()

        return RequirementRevision(
            requirement_id=UUID(row["requirement_id"]),
            revision_id=UUID(row["revision_id"]),
            revision_number=row["revision_number"],
            full_requirement=row["full_requirement"],
            supplemental_information=row["supplemental_information"],
            analyzed_requirement=_json_load(row["analyzed_requirement_json"]),
            changes=_CHANGES_ADAPTER.validate_python(
                _json_load(row["changes_json"])
            ),
            feedback=_FEEDBACK_ADAPTER.validate_python(
                [_json_load(item["payload_json"]) for item in feedback_rows]
            ),
            output_snapshot=_json_load(snapshot_row["payload_json"])
            if snapshot_row is not None
            else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class _SQLiteTransaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def __enter__(self) -> sqlite3.Connection:
        self._connection.execute("BEGIN IMMEDIATE")
        return self._connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=str)


def _json_load(payload: str | None) -> Any:
    if payload is None:
        return None
    return json.loads(payload)
