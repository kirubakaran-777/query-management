from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Query, QueryStatus


class QueryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.queries: dict[str, Query] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.queries = {}
            return
        content = self.path.read_text(encoding="utf-8").strip()
        if not content:
            self.queries = {}
            return
        data = json.loads(content)
        items = data.get("queries", []) if isinstance(data, dict) else data
        self.queries = {item["query_id"]: Query.from_dict(item) for item in items}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"queries": [query.to_dict() for query in self.queries.values()]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, query: Query) -> None:
        self.queries[query.query_id] = query
        self.save()

    def update(self, query: Query) -> None:
        self.queries[query.query_id] = query
        self.save()

    def get(self, query_id: str) -> Query | None:
        return self.queries.get(query_id)

    def list_queries(self, status: QueryStatus | None = None) -> Iterable[Query]:
        queries = self.queries.values()
        if status is not None:
            queries = [query for query in queries if query.status == status]
        return sorted(queries, key=lambda query: query.created_at)
