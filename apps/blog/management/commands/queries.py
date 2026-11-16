from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Count, Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Post
from apps.blog.queries import QUERIES

PREVIEW_ROWS = 5
DATA_CHANGING_QUERIES = range(40, 45)
SAMPLE_PAGE = 2
SAMPLE_WORD = "an"
SAMPLE_DOMAIN = "example.com"
SAMPLE_DAYS = 30
SAMPLE_RANGE_DAYS = 60
SAMPLE_CATEGORY_SLUGS = ["python", "django", "devops"]
MIN_TAGS_FOR_PAIR = 2
SAMPLE_CATEGORY_SLUG = "python"
SAMPLE_TAG_SLUG = "python"
SAMPLE_SECOND_TAG_SLUG = "django"
SAMPLE_MIN_POSTS = 10
NAME_SEARCH_LETTERS = 3
SAMPLE_TAG_NAME = "Django ORM"
SAMPLE_MERGE_SOURCE_SLUG = "career"
SAMPLE_MERGE_TARGET_SLUG = "python"


def post_slug_arguments() -> dict[str, Any]:
    return {"slug": Post.objects.values_list("slug", flat=True).first()}


def current_month_arguments() -> dict[str, Any]:
    today = timezone.localdate()
    return {"year": today.year, "month": today.month}


def date_range_arguments() -> dict[str, Any]:
    today = timezone.localdate()
    return {"start": today - timedelta(days=SAMPLE_RANGE_DAYS), "end": today}


def author_email_arguments() -> dict[str, Any]:
    email = (
        User.objects.filter(post__status=Post.Status.PUBLISHED)
        .values_list("email", flat=True)
        .first()
    )
    return {"email": email}


def tag_pair_arguments() -> dict[str, Any]:
    post = (
        Post.objects.annotate(tag_count=Count("tags"))
        .filter(tag_count__gte=MIN_TAGS_FOR_PAIR)
        .first()
    )
    if post is None:
        return {"first_slug": SAMPLE_TAG_SLUG, "second_slug": SAMPLE_SECOND_TAG_SLUG}
    first_slug, second_slug = post.tags.values_list("slug", flat=True)[:MIN_TAGS_FOR_PAIR]
    return {"first_slug": first_slug, "second_slug": second_slug}


def full_name_arguments() -> dict[str, Any]:
    user = User.objects.first()
    if user is None:
        return {"text": SAMPLE_WORD}
    return {"text": f"{user.first_name} {user.last_name[:NAME_SEARCH_LETTERS]}".lower()}


QUERY_ARGUMENTS: dict[int, dict[str, Any] | Callable[[], dict[str, Any]]] = {
    4: post_slug_arguments,
    7: {"page": SAMPLE_PAGE},
    8: {"word": SAMPLE_WORD},
    9: {"domain": SAMPLE_DOMAIN},
    11: {"slugs": SAMPLE_CATEGORY_SLUGS},
    12: current_month_arguments,
    13: {"days": SAMPLE_DAYS},
    14: date_range_arguments,
    15: author_email_arguments,
    16: {"tag_slug": SAMPLE_TAG_SLUG},
    17: {"category_slug": SAMPLE_CATEGORY_SLUG},
    21: tag_pair_arguments,
    22: {"text": SAMPLE_WORD},
    34: {"min_posts": SAMPLE_MIN_POSTS},
    37: full_name_arguments,
    40: {"name": SAMPLE_TAG_NAME},
    41: {"days": SAMPLE_DAYS},
    42: {"category_slug": SAMPLE_CATEGORY_SLUG, "tag_slug": SAMPLE_SECOND_TAG_SLUG},
    43: {"source_slug": SAMPLE_MERGE_SOURCE_SLUG, "target_slug": SAMPLE_MERGE_TARGET_SLUG},
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

        try:
            with CaptureQueriesContext(connection) as context:
                result = function(**arguments)
                if isinstance(result, QuerySet):
                    annotations = list(result.query.annotations)
                    result = list(result)
                else:
                    annotations = []
        except ObjectDoesNotExist as error:
            raise CommandError(
                f"#{number} {function.__name__} failed: {error} "
                "Run 'python manage.py seed --clear' to get fresh data."
            ) from error

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
