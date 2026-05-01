from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.i18n import DEFAULT_LANGUAGE


CATEGORY_NAME_MAX_LENGTH = 100
TAG_NAME_MAX_LENGTH = 50
POST_TITLE_MAX_LENGTH = 200
SLUG_MAX_LENGTH = 255


class Category(models.Model):
    name = models.CharField(_("English name"), max_length=CATEGORY_NAME_MAX_LENGTH, unique=True)
    name_ru = models.CharField(_("Russian name"), max_length=CATEGORY_NAME_MAX_LENGTH, default="")
    name_kk = models.CharField(_("Kazakh name"), max_length=CATEGORY_NAME_MAX_LENGTH, default="")
    slug = models.SlugField(_("slug"), max_length=SLUG_MAX_LENGTH, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self) -> str:
        return self.name

    def localized_name(self, language: str = DEFAULT_LANGUAGE) -> str:
        if language == "ru":
            return self.name_ru
        if language == "kk":
            return self.name_kk
        return self.name


class Tag(models.Model):
    name = models.CharField(_("name"), max_length=TAG_NAME_MAX_LENGTH, unique=True)
    slug = models.SlugField(_("slug"), max_length=SLUG_MAX_LENGTH, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("tag")
        verbose_name_plural = _("tags")

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        SCHEDULED = "scheduled", _("Scheduled")

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts", verbose_name=_("author"))
    title = models.CharField(_("title"), max_length=POST_TITLE_MAX_LENGTH)
    slug = models.SlugField(_("slug"), max_length=SLUG_MAX_LENGTH, unique=True)
    body = models.TextField(_("body"))
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="posts",
        null=True,
        blank=True,
        verbose_name=_("category"),
    )
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True, verbose_name=_("tags"))
    status = models.CharField(_("status"), max_length=20, choices=Status.choices, default=Status.DRAFT)
    publish_at = models.DateTimeField(_("publish at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("post")
        verbose_name_plural = _("posts")

    def __str__(self) -> str:
        return self.title

    @property
    def published_at(self):
        return self.publish_at or self.updated_at or timezone.now()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments", verbose_name=_("post"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments", verbose_name=_("author"))
    body = models.TextField(_("body"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self) -> str:
        return f"Comment by {self.author_id} on {self.post_id}"
