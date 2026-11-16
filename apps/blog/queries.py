from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    CharField,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

NEWEST_POSTS_LIMIT = 5
PAGE_SIZE = 10
EMAIL_DOMAIN_PREFIX = "@"
EDIT_THRESHOLD = timedelta(hours=1)
UNCATEGORIZED = "Uncategorized"
AVERAGE_PRECISION = 2
EMPTY_AVERAGE = 0.0
TOP_AUTHORS_LIMIT = 5
FULL_NAME_SEPARATOR = " "
HOT_MIN_COMMENTS = 10
NORMAL_MIN_COMMENTS = 3
POPULARITY_HOT = "hot"
POPULARITY_NORMAL = "normal"
POPULARITY_QUIET = "quiet"
FEED_LIMIT = 50
FEED_SEPARATOR = " | "
NEWEST_WITH_TAGS_LIMIT = 20
TAGS_SEPARATOR = ", "


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


def author_published_posts(email: str) -> QuerySet[Post]:
    """Published posts of the author with this email, ignoring letter case."""
    return Post.objects.filter(author__email__iexact=email, status=Post.Status.PUBLISHED)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Posts that have the tag with this slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Comments on posts of the category with this slug."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Users with at least one published post, each user once."""
    return User.objects.filter(post__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Users who have never written a comment."""
    return User.objects.filter(comment__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Posts that have both tags."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)


def search_posts(text: str) -> QuerySet[Post]:
    """Posts with the text in the title or in the body, ignoring letter case."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Published posts without a category or without tags, each post once."""
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Posts edited more than EDIT_THRESHOLD after they were created."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDIT_THRESHOLD)


def comments_by_post_author() -> QuerySet[Comment]:
    """Comments written by the author of the post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """Comments created before their post."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


def published_authors_emails() -> list[str]:
    """Unique emails of authors with published posts, sorted A to Z."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .values_list("author__email", flat=True)
        .distinct()
        .order_by("author__email")
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """Title, author email and category name of every published post."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED).values(
            "title",
            author_email=F("author__email"),
            category_name=Coalesce(F("category__name"), Value(UNCATEGORIZED)),
        )
    )


def posts_stats() -> dict[str, Any]:
    """Post counts and the dates of the first and the last post in one query."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Average number of comments on a published post, rounded to 2 digits."""
    result = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comment"))
        .aggregate(average=Avg("comment_count", default=EMPTY_AVERAGE))
    )
    return round(result["average"], AVERAGE_PRECISION)


def categories_with_post_count() -> QuerySet[Category]:
    """Every category with post_count, most posts first, then by name."""
    return Category.objects.annotate(post_count=Count("post")).order_by("-post_count", "name")


def categories_with_published_count() -> QuerySet[Category]:
    """Every category with published_count, including categories with 0."""
    return Category.objects.annotate(
        published_count=Count("post", filter=Q(post__status=Post.Status.PUBLISHED))
    ).order_by("name")


def top_authors() -> QuerySet[User]:
    """Top 5 users by number of published posts, with published_count."""
    return User.objects.annotate(
        published_count=Count("post", filter=Q(post__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Tags used in at least min_posts posts, with post_count."""
    return (
        Tag.objects.annotate(post_count=Count("post"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )


def posts_per_status() -> list[dict[str, Any]]:
    """Number of posts for each status."""
    return list(Post.objects.values("status").annotate(count=Count("id")).order_by("status"))


def users_activity() -> QuerySet[User]:
    """Every user with post_count and comment_count."""
    return User.objects.annotate(
        post_count=Count("post", distinct=True),
        comment_count=Count("comment", distinct=True),
    ).order_by("email")


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Users whose full name contains the text, ignoring letter case."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(FULL_NAME_SEPARATOR), "last_name")
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Number of published posts in each month, oldest month first."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Every post with comment_count and popularity: hot, normal or quiet."""
    return Post.objects.annotate(comment_count=Count("comment")).annotate(
        popularity=Case(
            When(comment_count__gte=HOT_MIN_COMMENTS, then=Value(POPULARITY_HOT)),
            When(comment_count__gte=NORMAL_MIN_COMMENTS, then=Value(POPULARITY_NORMAL)),
            default=Value(POPULARITY_QUIET),
            output_field=CharField(),
        )
    )


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Return the tag with this name, create it if it does not exist."""
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """Publish all drafts older than `days` days with one query."""
    now = timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT, created_at__lt=now - timedelta(days=days)
    ).update(status=Post.Status.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add the tag to every post of the category and return the number of posts."""
    tag = Tag.objects.get(slug=tag_slug)
    post_ids = list(Post.objects.filter(category__slug=category_slug).values_list("id", flat=True))
    tag.post_set.add(*post_ids)
    return len(post_ids)


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move all posts of the source category to the target and delete the source."""
    with transaction.atomic():
        source = Category.objects.get(slug=source_slug)
        target = Category.objects.get(slug=target_slug)
        moved = Post.objects.filter(category=source).update(category=target)
        source.delete()
    return moved


def delete_inactive_users_comments() -> int:
    """Delete all comments written by inactive users."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


def published_feed() -> list[str]:
    """The 50 newest published posts as 'title | author email | category name'."""
    posts = published_posts().select_related("author", "category")[:FEED_LIMIT]
    return [
        FEED_SEPARATOR.join(
            [post.title, post.author.email, post.category.name if post.category else UNCATEGORIZED]
        )
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """The 20 newest posts as 'title: tag1, tag2'."""
    posts = Post.objects.prefetch_related("tags").order_by("-created_at")[:NEWEST_WITH_TAGS_LIMIT]
    return [
        f"{post.title}: {TAGS_SEPARATOR.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    """Category name mapped to the titles of its published posts, newest first."""
    categories = Category.objects.order_by("name").prefetch_related(
        Prefetch("post_set", queryset=published_posts(), to_attr="published_posts")
    )
    return {
        category.name: [post.title for post in category.published_posts] for category in categories
    }


def posts_with_last_comment() -> QuerySet[Post]:
    """Published posts with last_comment, the body of the newest comment."""
    newest_comments = Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at")
    return published_posts().annotate(last_comment=Subquery(newest_comments.values("body")[:1]))


def posts_with_staff_comments() -> QuerySet[Post]:
    """Posts with at least one comment from a staff user."""
    staff_comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Users whose newest post is a draft, with latest_post_status."""
    latest_posts = Post.objects.filter(author=OuterRef("pk")).order_by("-created_at")
    return User.objects.annotate(
        latest_post_status=Subquery(latest_posts.values("status")[:1])
    ).filter(latest_post_status=Post.Status.DRAFT)


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
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
