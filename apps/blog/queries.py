from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Category, Post

NEWEST_POSTS_LIMIT = 5
PAGE_SIZE = 10
EMAIL_DOMAIN_PREFIX = "@"


def categories_by_name() -> QuerySet[Category]:
    """All categories sorted by name A to Z."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """The 5 newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """The post with this slug or None."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Number of active users who are not staff."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """True if there is at least one draft post."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """One page of published posts, newest first, PAGE_SIZE posts per page."""
    start = (page - 1) * PAGE_SIZE
    return published_posts()[start : start + PAGE_SIZE]


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Posts whose title contains the word, ignoring letter case."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Users whose email ends with @domain."""
    return User.objects.filter(email__iendswith=f"{EMAIL_DOMAIN_PREFIX}{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Posts that have no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Categories whose slug is in the list."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Posts created in this month of this year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Posts created in the last `days` days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Posts created from start to end, both days included."""
    return Post.objects.filter(created_at__date__range=(start, end))


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
}
