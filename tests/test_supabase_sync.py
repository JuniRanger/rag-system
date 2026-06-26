import pytest

from app.ingestion.loaders.supabase_loader import SupabaseLoader
from app.ingestion.supabase_sync import SupabaseSyncService


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *_args, **_kwargs):
        return self

    def gt(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self._start = start
        self._end = end
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def single(self):
        return self

    def execute(self):
        rows = list(self._rows)

        for column, value in self._filters:
            if isinstance(value, tuple):
                continue
            rows = [row for row in rows if row.get(column) == value or row.get(column) > value]

        if hasattr(self, "_start"):
            rows = rows[self._start : self._end + 1]

        if any(filter_item[0] == "id" and isinstance(filter_item[1], int) for filter_item in self._filters):
            rows = [row for row in self._rows if row["id"] == self._filters[-1][1]]

        return type("Response", (), {"data": rows if rows else None})()


class FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _name):
        return FakeQuery(self._rows)


def test_supabase_loader_build_text_with_selected_columns():
    loader = SupabaseLoader(
        FakeClient([]),
        table="articles",
        text_columns=["title", "body"],
    )

    text = loader.build_text({"id": 1, "title": "Hola", "body": "Mundo", "internal": "x"})

    assert "id: 1" in text
    assert "title: Hola" in text
    assert "body: Mundo" in text
    assert "internal" not in text


def test_supabase_loader_fetch_all_tracks_last_cursor():
    rows = [
        {"id": 1, "title": "A", "content": "alpha"},
        {"id": 2, "title": "B", "content": "beta"},
    ]
    loader = SupabaseLoader(FakeClient(rows), table="articles", text_columns=["title", "content"])

    documents, last_cursor = loader.fetch_all()

    assert len(documents) == 2
    assert documents[0]["metadata"]["record_id"] == 1
    assert last_cursor == 2


def test_webhook_ignores_non_insert_events():
    from unittest.mock import patch

    with patch.object(SupabaseSyncService, "__init__", lambda self: None):
        service = SupabaseSyncService()
        service.table = "articles"

        with patch("app.ingestion.supabase_sync.settings") as mock_settings:
            mock_settings.SUPABASE_TABLE = "articles"
            result = service.ingest_webhook_record(
                {
                    "type": "UPDATE",
                    "table": "articles",
                    "record": {"id": 1, "title": "Nuevo"},
                }
            )

    assert result["success"] is True
    assert result["chunks_created"] == 0
