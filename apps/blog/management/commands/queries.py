from collections.abc import Callable
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext

from apps.blog.models import Post
from apps.blog.queries import QUERIES

PREVIEW_ROWS = 5
DATA_CHANGING_QUERIES = range(40, 45)
SAMPLE_PAGE = 2


def post_slug_arguments() -> dict[str, Any]:
    return {"slug": Post.objects.values_list("slug", flat=True).first()}


QUERY_ARGUMENTS: dict[int, dict[str, Any] | Callable[[], dict[str, Any]]] = {
    4: post_slug_arguments,
    7: {"page": SAMPLE_PAGE},
}


class Command(BaseCommand):
    help = "Run the ORM queries from apps/blog/queries.py."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only the query with this number")
        parser.add_argument("--sql", action="store_true", help="Print the SQL of every query")

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is None:
            numbers = [key for key in QUERIES if key not in DATA_CHANGING_QUERIES]
        elif number in QUERIES:
            numbers = [number]
        else:
            raise CommandError(f"Query #{number} does not exist. Use 1-{len(QUERIES)}.")

        for query_number in numbers:
            self.run_query(query_number, show_sql)

    def run_query(self, number: int, show_sql: bool) -> None:
        function = QUERIES[number]
        arguments = self.get_arguments(number)

        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotations)
                result = list(result)
            else:
                annotations = []

        count = len(context.captured_queries)
        word = "query" if count == 1 else "queries"
        self.stdout.write(
            self.style.SUCCESS(f"#{number} {function.__name__} — {count} SQL {word}")
        )
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(captured["sql"])
        self.write_result(result, annotations)

    def get_arguments(self, number: int) -> dict[str, Any]:
        arguments = QUERY_ARGUMENTS.get(number, {})
        if callable(arguments):
            return arguments()
        return arguments

    def write_result(self, result: Any, annotations: list[str]) -> None:
        if isinstance(result, dict):
            rows = [f"{key}: {value}" for key, value in result.items()]
        elif isinstance(result, list):
            rows = [self.format_row(row, annotations) for row in result]
        else:
            self.stdout.write(f"  {self.format_row(result, annotations)}")
            return

        for row in rows[:PREVIEW_ROWS]:
            self.stdout.write(f"  {row}")
        self.stdout.write(f"  ({len(rows)} rows)")

    def format_row(self, row: Any, annotations: list[str]) -> str:
        if isinstance(row, Model) and annotations:
            values = {name: getattr(row, name) for name in annotations}
            return f"{row} {values}"
        return str(row)
