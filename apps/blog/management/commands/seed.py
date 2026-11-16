import random
import time
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

SEED_PASSWORD = "SeedPass123!"
EMAIL_DOMAINS = ["example.com", "mail.com", "blog.dev"]
EMAIL_SEPARATOR = "."

INACTIVE_USERS_RATIO = 0.1
STAFF_USERS_RATIO = 0.05
MIN_USERS_PER_ROLE = 1

PUBLISHED_RATIO = 0.7
NO_CATEGORY_RATIO = 0.1
MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
MIN_TITLE_WORDS = 3
MAX_TITLE_WORDS = 8
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
BODY_TEMPLATE = "<div>{}</div>"
PARAGRAPH_SEPARATOR = "<br><br>"
TITLE_END = "."
SLUG_SUFFIX_START = 2

DATE_RANGE_DAYS = 365
EDITED_POST_RATIO = 0.3
MIN_EDIT_DELAY_DAYS = 1
MAX_EDIT_DELAY_DAYS = 30

MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

BATCH_SIZE = 500
LABEL_WIDTH = 11
COUNT_WIDTH = 4
SECONDS_PRECISION = 2

CATEGORY_NAMES = [
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Career",
    "Security",
    "Machine Learning",
]

TAG_NAMES = [
    "python",
    "django",
    "rest-api",
    "orm",
    "postgresql",
    "sqlite",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "testing",
    "performance",
    "javascript",
    "react",
    "css",
    "security",
    "career",
    "interview",
    "tutorial",
    "best-practices",
]


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users", type=int, default=DEFAULT_USERS, help="Number of users to create"
        )
        parser.add_argument(
            "--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create"
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Delete existing data before seeding"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        self.validate_counts(users=users_count, posts=posts_count, comments=comments_count)

        self.fake = Faker()
        started_at = time.perf_counter()

        with transaction.atomic():
            if clear:
                self.clear_data()

            users = self.create_users(users_count)
            categories = self.create_categories()
            tags = self.create_tags()

            authors = list(User.objects.filter(is_superuser=False))
            if (posts_count or comments_count) and not authors:
                raise CommandError("Cannot create posts or comments: there are no users.")

            existing_published = list(
                Post.objects.filter(status=Post.Status.PUBLISHED).only("id", "created_at")
            )
            posts = self.create_posts(posts_count, authors)
            published = existing_published + [
                post for post in posts if post.status == Post.Status.PUBLISHED
            ]
            if comments_count and not published:
                raise CommandError("Cannot create comments: there are no published posts.")

            comments = self.create_comments(comments_count, published, authors)

        elapsed = time.perf_counter() - started_at
        if clear:
            self.stdout.write(self.style.WARNING("Existing data deleted."))
        self.write_summary("Users:", len(users))
        self.write_summary("Categories:", len(categories))
        self.write_summary("Tags:", len(tags))
        self.write_summary("Posts:", len(posts))
        self.write_summary("Comments:", len(comments))
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.{SECONDS_PRECISION}f} seconds"))

    def validate_counts(self, **counts: int) -> None:
        for name, value in counts.items():
            if value < 0:
                raise CommandError(f"--{name} must not be negative, got {value}.")

    def clear_data(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def create_users(self, count: int) -> list[User]:
        if not count:
            return []

        used_emails = set(User.objects.values_list("email", flat=True))
        password = make_password(SEED_PASSWORD)
        order = random.sample(range(count), count)
        inactive_count = max(MIN_USERS_PER_ROLE, round(count * INACTIVE_USERS_RATIO))
        staff_count = max(MIN_USERS_PER_ROLE, round(count * STAFF_USERS_RATIO))
        inactive_indexes = set(order[:inactive_count])
        staff_indexes = set(order[inactive_count : inactive_count + staff_count])

        users = []
        for index in range(count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            users.append(
                User(
                    email=self.build_unique_email(first_name, last_name, used_emails),
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=index not in inactive_indexes,
                    is_staff=index in staff_indexes,
                )
            )
        return User.objects.bulk_create(users, batch_size=BATCH_SIZE)

    def build_unique_email(self, first_name: str, last_name: str, used_emails: set[str]) -> str:
        local_part = slugify(f"{first_name} {last_name}").replace("-", EMAIL_SEPARATOR)
        domain = random.choice(EMAIL_DOMAINS)
        email = f"{local_part}@{domain}"
        suffix = SLUG_SUFFIX_START
        while email in used_emails:
            email = f"{local_part}{suffix}@{domain}"
            suffix += 1
        used_emails.add(email)
        return email

    def create_categories(self) -> list[Category]:
        existing = set(Category.objects.values_list("slug", flat=True))
        categories = [
            Category(name=name, slug=slugify(name))
            for name in CATEGORY_NAMES
            if slugify(name) not in existing
        ]
        return Category.objects.bulk_create(categories)

    def create_tags(self) -> list[Tag]:
        existing = set(Tag.objects.values_list("slug", flat=True))
        tags = [
            Tag(name=name, slug=slugify(name))
            for name in TAG_NAMES
            if slugify(name) not in existing
        ]
        return Tag.objects.bulk_create(tags)

    def create_posts(self, count: int, authors: list[User]) -> list[Post]:
        if not count:
            return []

        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())
        used_slugs = set(Post.objects.values_list("slug", flat=True))

        posts = []
        for _ in range(count):
            title = self.fake.sentence(
                nb_words=random.randint(MIN_TITLE_WORDS, MAX_TITLE_WORDS)
            ).rstrip(TITLE_END)
            paragraphs = self.fake.paragraphs(nb=random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS))
            is_published = random.random() < PUBLISHED_RATIO
            has_category = bool(categories) and random.random() >= NO_CATEGORY_RATIO
            posts.append(
                Post(
                    author=random.choice(authors),
                    title=title,
                    slug=self.build_unique_slug(title, used_slugs),
                    body=BODY_TEMPLATE.format(PARAGRAPH_SEPARATOR.join(paragraphs)),
                    category=random.choice(categories) if has_category else None,
                    status=Post.Status.PUBLISHED if is_published else Post.Status.DRAFT,
                )
            )

        posts = Post.objects.bulk_create(posts, batch_size=BATCH_SIZE)
        self.spread_post_dates(posts)

        for post in posts:
            tags_count = random.randint(MIN_TAGS_PER_POST, min(MAX_TAGS_PER_POST, len(tags)))
            post.tags.set(random.sample(tags, tags_count))

        return posts

    def spread_post_dates(self, posts: list[Post]) -> None:
        now = timezone.now()
        for post in posts:
            post.created_at = self.random_date_between(now - timedelta(days=DATE_RANGE_DAYS), now)
            post.updated_at = post.created_at
            if random.random() < EDITED_POST_RATIO:
                delay = timedelta(days=random.randint(MIN_EDIT_DELAY_DAYS, MAX_EDIT_DELAY_DAYS))
                post.updated_at = min(post.created_at + delay, now)

        Post.objects.bulk_update(posts, ["created_at", "updated_at"], batch_size=BATCH_SIZE)

    def random_date_between(self, start: datetime, end: datetime) -> datetime:
        seconds = int((end - start).total_seconds())
        return start + timedelta(seconds=random.randint(0, seconds))

    def build_unique_slug(self, title: str, used_slugs: set[str]) -> str:
        base_slug = slugify(title)
        slug = base_slug
        suffix = SLUG_SUFFIX_START
        while slug in used_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        return slug

    def create_comments(self, count: int, posts: list[Post], authors: list[User]) -> list[Comment]:
        if not count:
            return []

        comments = [
            Comment(
                post=random.choice(posts),
                author=random.choice(authors),
                body=self.fake.paragraph(
                    nb_sentences=random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES),
                    variable_nb_sentences=False,
                ),
            )
            for _ in range(count)
        ]

        comments = Comment.objects.bulk_create(comments, batch_size=BATCH_SIZE)
        self.spread_comment_dates(comments)
        return comments

    def spread_comment_dates(self, comments: list[Comment]) -> None:
        now = timezone.now()
        for comment in comments:
            comment.created_at = self.random_date_between(comment.post.created_at, now)
        Comment.objects.bulk_update(comments, ["created_at"], batch_size=BATCH_SIZE)

    def write_summary(self, label: str, count: int) -> None:
        self.stdout.write(f"{label:<{LABEL_WIDTH}}{count:>{COUNT_WIDTH}} created")
