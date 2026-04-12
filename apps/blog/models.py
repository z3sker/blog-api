from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


class Category(models.Model):
    name_en = models.CharField(max_length=100, unique=True, verbose_name=_("name (English)"))
    name_ru = models.CharField(max_length=100, unique=True, verbose_name=_("name (Russian)"))
    name_kk = models.CharField(max_length=100, unique=True, verbose_name=_("name (Kazakh)"))
    slug = models.SlugField(unique=True, verbose_name=_("slug"))

    class Meta:
        ordering = ("name_en",)

    @property
    def name(self) -> str:
        lang = (get_language() or "en").split("-")[0]
        if lang == "ru":
            return self.name_ru
        if lang == "kk":
            return self.name_kk
        return self.name_en

    def __str__(self) -> str:
        return self.name_en


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("name"))
    slug = models.SlugField(unique=True, verbose_name=_("slug"))

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class PostStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("author"),
    )
    title = models.CharField(max_length=200, verbose_name=_("title"))
    slug = models.SlugField(unique=True, verbose_name=_("slug"))
    body = models.TextField(verbose_name=_("body"))
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("category"),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts", verbose_name=_("tags"))
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT,
        verbose_name=_("status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("author"),
    )
    body = models.TextField(verbose_name=_("body"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Comment #{self.pk}"

# Create your models here.
