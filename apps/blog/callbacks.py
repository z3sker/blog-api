import json
from typing import Any

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpRequest

from apps.auths.models import User
from apps.blog.constants import PERCENT, TOP_AUTHORS_LIMIT, UNCATEGORIZED_LABEL
from apps.blog.models import Category, Comment, Post

PRODUCTION_ENV_ID = "prod"
LOCAL_ENVIRONMENT = ["Local", "warning"]
PRODUCTION_ENVIRONMENT = ["Production", "danger"]
CHART_COLOR = "var(--color-primary-600)"
CHART_BAR_THICKNESS = 28


def environment_callback(request: HttpRequest) -> list[str]:
    if settings.ENV_ID == PRODUCTION_ENV_ID:
        return PRODUCTION_ENVIRONMENT
    return LOCAL_ENVIRONMENT


def drafts_badge(request: HttpRequest) -> int:
    return Post.objects.filter(status=Post.Status.DRAFT).count()


def percent(part: int, total: int) -> int:
    if not total:
        return 0
    return round(part * PERCENT / total)


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    post_stats = Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        uncategorized=Count("id", filter=Q(category__isnull=True)),
    )
    categories = list(
        Category.objects.annotate(post_count=Count("post"))
        .order_by("-post_count", "name")
        .values_list("name", "post_count")
    )
    top_authors = (
        User.objects.annotate(post_count=Count("post"))
        .filter(post_count__gt=0)
        .order_by("-post_count", "email")[:TOP_AUTHORS_LIMIT]
    )

    labels = [name for name, _ in categories] + [UNCATEGORIZED_LABEL]
    values = [count for _, count in categories] + [post_stats["uncategorized"]]
    published_percent = percent(post_stats["published"], post_stats["total"])
    drafts_percent = percent(post_stats["drafts"], post_stats["total"])

    context.update(
        {
            "cards": [
                {"title": "Total users", "value": User.objects.count(), "icon": "group"},
                {
                    "title": "Published posts",
                    "value": post_stats["published"],
                    "icon": "check_circle",
                },
                {"title": "Drafts", "value": post_stats["drafts"], "icon": "edit_note"},
                {"title": "Comments", "value": Comment.objects.count(), "icon": "chat"},
            ],
            "posts_per_category_chart": json.dumps(
                {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Posts",
                            "data": values,
                            "backgroundColor": CHART_COLOR,
                            "maxBarThickness": CHART_BAR_THICKNESS,
                        }
                    ],
                }
            ),
            "top_authors_table": {
                "headers": ["Author", "Email", "Posts"],
                "rows": [
                    [author.get_full_name(), author.email, author.post_count]
                    for author in top_authors
                ],
            },
            "status_progress": [
                {
                    "title": "Published",
                    "description": f"{post_stats['published']} posts · {published_percent}%",
                    "value": published_percent,
                },
                {
                    "title": "Drafts",
                    "description": f"{post_stats['drafts']} posts · {drafts_percent}%",
                    "value": drafts_percent,
                },
            ],
        }
    )
    return context
