from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from ...models import Category, Comment, Post, PostStatus, Tag

logger = logging.getLogger("blog")

USER_PASSWORD = "password12345"


class Command(BaseCommand):
    help = "Seed database with test data."

    def handle(self, *args, **options) -> None:
        if Post.objects.exists():
            self.stdout.write("Seed skipped: posts already exist.")
            return

        User = get_user_model()
        users = []
        for i in range(1, 6):
            email = f"user{i}@example.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": f"User{i}",
                    "last_name": "Test",
                    "language": "en",
                    "timezone": "UTC",
                },
            )
            if created:
                user.set_password(USER_PASSWORD)
                user.save(update_fields=["password"])
            users.append(user)

        categories_data = [
            ("Technology", "Технологии", "Технология", "tech"),
            ("Travel", "Путешествия", "Саяхат", "travel"),
            ("Food", "Еда", "Тағам", "food"),
        ]
        categories = []
        for name_en, name_ru, name_kk, slug in categories_data:
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_en": name_en, "name_ru": name_ru, "name_kk": name_kk},
            )
            categories.append(category)

        tags_data = ["django", "redis", "asyncio", "rest", "testing"]
        tags = []
        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name.title(), slug=tag_name)
            tags.append(tag)

        for idx in range(1, 31):
            author = users[idx % len(users)]
            title = f"Sample post {idx}"
            slug = slugify(title)
            status_value = PostStatus.PUBLISHED if idx <= 25 else PostStatus.DRAFT
            post = Post.objects.create(
                author=author,
                title=title,
                slug=slug,
                body=f"Body for post {idx}.",
                category=categories[idx % len(categories)],
                status=status_value,
            )
            post.tags.set(tags[: (idx % len(tags)) + 1])

            for c in range(1, 4):
                Comment.objects.create(
                    post=post,
                    author=users[(idx + c) % len(users)],
                    body=f"Comment {c} for post {idx}.",
                )

        logger.info("Seed completed: users=%s posts=%s", len(users), Post.objects.count())
        self.stdout.write("Seed completed.")
