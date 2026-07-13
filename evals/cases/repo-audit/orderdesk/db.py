"""Thin database access layer.

Prefer `query()` / `execute()` — they bind parameters and are injection-safe.
`raw_query()` runs a pre-built SQL string and exists for a few static,
developer-authored analytics statements that take no external input.
"""
from typing import Any, Sequence


class Database:
    def __init__(self, url: str) -> None:
        self._url = url
        self._conn = _connect(url)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict]:
        """Parameterized read. `sql` uses %s placeholders bound to `params`."""
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()

    def raw_query(self, sql: str) -> list[dict]:
        """Run an already-assembled SQL string verbatim (no binding)."""
        cur = self._conn.cursor()
        cur.execute(sql)
        return cur.fetchall()


def _connect(url: str):  # pragma: no cover - fixture stub
    raise NotImplementedError("fixture: no real DB driver")
