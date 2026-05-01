from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.blog.models import Category, Comment, Post, Tag


USER_PASSWORD = "Testpass123!"
POST_COUNT = 16


class Command(BaseCommand):
    help = "Seed realistic local development data."

    def handle(self, *args: object, **options: object) -> None:
        user_model = get_user_model()
        users = [
            user_model.objects.get_or_create(
                email="alice@example.com",
                defaults={"first_name": "Alice", "last_name": "Adams", "language": "en", "timezone": "UTC"},
            )[0],
            user_model.objects.get_or_create(
                email="boris@example.com",
                defaults={"first_name": "Boris", "last_name": "Ivanov", "language": "ru", "timezone": "Europe/Moscow"},
            )[0],
            user_model.objects.get_or_create(
                email="aigerim@example.com",
                defaults={"first_name": "Aigerim", "last_name": "Smailova", "language": "kk", "timezone": "Asia/Almaty"},
            )[0],
        ]
        for user in users:
            if not user.has_usable_password():
                user.set_password(USER_PASSWORD)
                user.save(update_fields=["password"])

        categories = [
            Category.objects.get_or_create(
                slug="technology",
                defaults={"name": "Technology", "name_ru": "Технологии", "name_kk": "Технология"},
            )[0],
            Category.objects.get_or_create(
                slug="life",
                defaults={"name": "Life", "name_ru": "Жизнь", "name_kk": "Өмір"},
            )[0],
            Category.objects.get_or_create(
                slug="education",
                defaults={"name": "Education", "name_ru": "Образование", "name_kk": "Білім"},
            )[0],
        ]
        tags = [
            Tag.objects.get_or_create(name="django", slug="django")[0],
            Tag.objects.get_or_create(name="api", slug="api")[0],
            Tag.objects.get_or_create(name="redis", slug="redis")[0],
            Tag.objects.get_or_create(name="async", slug="async")[0],
        ]

        for index in range(1, POST_COUNT + 1):
            author = users[index % len(users)]
            category = categories[index % len(categories)]
            status = Post.Status.PUBLISHED if index % 4 else Post.Status.DRAFT
            post, _created = Post.objects.get_or_create(
                slug=f"seed-post-{index}",
                defaults={
                    "author": author,
                    "category": category,
                    "title": f"Seed post {index}",
                    "body": "This post exists so pagination, filtering, comments, and localization can be tested.",
                    "status": status,
                },
            )
            post.tags.set(tags[: (index % len(tags)) + 1])
            for user in users:
                Comment.objects.get_or_create(
                    post=post,
                    author=user,
                    body=f"Comment from {user.first_name} on {post.slug}",
                )

        self.stdout.write(self.style.SUCCESS("Seed data is ready."))
