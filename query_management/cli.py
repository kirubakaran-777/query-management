from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from textwrap import shorten
from uuid import uuid4

from .models import Query, QueryStatus
from .store import QueryStore
from .workflow import allowed_transitions, can_transition, render_workflow_graph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query management application",
    )
    parser.add_argument(
        "--data-file",
        default="data/queries.json",
        help="Path to the JSON data store (default: data/queries.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new query")
    create_parser.add_argument("--customer", required=True, help="Customer name")
    create_parser.add_argument("--subject", required=True, help="Short subject")
    create_parser.add_argument("--description", required=True, help="Detailed description")
    create_parser.add_argument(
        "--priority",
        default="MEDIUM",
        choices=["LOW", "MEDIUM", "HIGH"],
        help="Priority level",
    )
    create_parser.add_argument("--assignee", help="Assigned agent")

    list_parser = subparsers.add_parser("list", help="List existing queries")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="Output format",
    )

    show_parser = subparsers.add_parser("show", help="Show a query by ID")
    show_parser.add_argument("query_id", help="Query identifier")

    status_parser = subparsers.add_parser("update-status", help="Update query status")
    status_parser.add_argument("query_id", help="Query identifier")
    status_parser.add_argument("status", help="New status")
    status_parser.add_argument("--note", help="Optional status change note")

    response_parser = subparsers.add_parser("add-response", help="Add a response")
    response_parser.add_argument("query_id", help="Query identifier")
    response_parser.add_argument("message", help="Response message")
    response_parser.add_argument("--author", help="Response author")

    workflow_parser = subparsers.add_parser("workflow", help="Print workflow graph")
    workflow_parser.add_argument(
        "--format",
        default="mermaid",
        choices=["mermaid", "dot", "text"],
        help="Graph format",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store = QueryStore(Path(args.data_file))

    if args.command == "create":
        return command_create(store, args)
    if args.command == "list":
        return command_list(store, args)
    if args.command == "show":
        return command_show(store, args)
    if args.command == "update-status":
        return command_update_status(store, args)
    if args.command == "add-response":
        return command_add_response(store, args)
    if args.command == "workflow":
        return command_workflow(args)

    parser.error("Unknown command")
    return 1


def command_create(store: QueryStore, args: argparse.Namespace) -> int:
    query_id = str(uuid4())
    query = Query.create(
        query_id=query_id,
        customer=args.customer,
        subject=args.subject,
        description=args.description,
        priority=args.priority,
        assignee=args.assignee,
    )
    store.add(query)
    print(f"Created query {query.query_id}")
    print_summary(query)
    return 0


def command_list(store: QueryStore, args: argparse.Namespace) -> int:
    status = parse_status(args.status) if args.status else None
    queries = list(store.list_queries(status=status))
    if args.format == "json":
        print(json.dumps([query.to_dict() for query in queries], indent=2))
        return 0
    print_table(queries)
    return 0


def command_show(store: QueryStore, args: argparse.Namespace) -> int:
    query = store.get(args.query_id)
    if not query:
        print(f"Query {args.query_id} not found")
        return 1
    print_details(query)
    return 0


def command_update_status(store: QueryStore, args: argparse.Namespace) -> int:
    query = store.get(args.query_id)
    if not query:
        print(f"Query {args.query_id} not found")
        return 1
    new_status = parse_status(args.status)
    if not can_transition(query.status, new_status):
        allowed = ", ".join(status.value for status in allowed_transitions(query.status))
        print(
            "Cannot transition from "
            f"{query.status.value} to {new_status.value}. "
            f"Allowed: {allowed or 'none'}."
        )
        return 1
    query.update_status(new_status, args.note)
    store.update(query)
    print(f"Updated query {query.query_id} to {query.status.value}")
    return 0


def command_add_response(store: QueryStore, args: argparse.Namespace) -> int:
    query = store.get(args.query_id)
    if not query:
        print(f"Query {args.query_id} not found")
        return 1
    query.add_response(args.message, args.author)
    store.update(query)
    print(f"Added response to {query.query_id}")
    return 0


def command_workflow(args: argparse.Namespace) -> int:
    print(render_workflow_graph(args.format))
    return 0


def print_summary(query: Query) -> None:
    print(
        f"Status: {query.status.value} | Priority: {query.priority} "
        f"| Updated: {query.updated_at}"
    )


def print_table(queries: list[Query]) -> None:
    if not queries:
        print("No queries found.")
        return
    headers = ["ID", "Customer", "Subject", "Status", "Priority", "Updated"]
    rows = [
        [
            query.query_id.split("-")[0],
            _shorten(query.customer, 18),
            _shorten(query.subject, 26),
            query.status.value,
            query.priority,
            query.updated_at.split("T")[0],
        ]
        for query in queries
    ]
    widths = [max(len(row[index]) for row in ([headers] + rows)) for index in range(len(headers))]
    print(" ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print(" ".join("-" * width for width in widths))
    for row in rows:
        print(" ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def print_details(query: Query) -> None:
    print(f"ID: {query.query_id}")
    print(f"Customer: {query.customer}")
    print(f"Subject: {query.subject}")
    print(f"Description: {query.description}")
    print(f"Status: {query.status.value}")
    print(f"Priority: {query.priority}")
    print(f"Assignee: {query.assignee or 'Unassigned'}")
    print(f"Created: {query.created_at}")
    print(f"Updated: {query.updated_at}")

    if query.responses:
        print("Responses:")
        for response in query.responses:
            author = response.author or "Unknown"
            print(f"- {response.created_at} ({author}): {response.message}")
    else:
        print("Responses: None")

    if query.history:
        print("History:")
        for entry in query.history:
            note = f" | Note: {entry.note}" if entry.note else ""
            print(
                f"- {entry.changed_at}: {entry.from_status} -> {entry.to_status}{note}"
            )
    else:
        print("History: None")


def _shorten(value: str, width: int) -> str:
    return shorten(value, width=width, placeholder="…")


def parse_status(value: str) -> QueryStatus:
    return QueryStatus.from_value(value)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        print(exc)
        sys.exit(2)
