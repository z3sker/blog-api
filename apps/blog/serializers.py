from __future__ import annotations

import logging

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils.text import slugify
from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _

from .models import Category, Comment, Post, PostStatus, Tag

logger = logging.getLogger("blog")
User = get_user_model()

MAX_SLUG_LENGTH = 50


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class PostReadSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    category = CategorySerializer(allow_null=True)
    tags = TagSerializer(many=True)
    created_at_display = serializers.SerializerMethodField()
    updated_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "tags",
            "status",
            "created_at",
            "updated_at",
            "created_at_display",
            "updated_at_display",
        )

    def get_author(self, obj: Post) -> dict:
        return {
            "id": obj.author_id,
            "email": obj.author.email,
            "first_name": obj.author.first_name,
            "last_name": obj.author.last_name,
        }

    def get_created_at_display(self, obj: Post) -> str:
        dt = timezone.localtime(obj.created_at)
        return formats.date_format(dt, format="DATETIME_FORMAT", use_l10n=True)

    def get_updated_at_display(self, obj: Post) -> str:
        dt = timezone.localtime(obj.updated_at)
        return formats.date_format(dt, format="DATETIME_FORMAT", use_l10n=True)


class PostWriteSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
    )
    tags = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Tag.objects.all(),
        many=True,
        required=False,
    )
    status = serializers.ChoiceField(choices=PostStatus.choices, required=False)
    slug = serializers.SlugField(required=False, allow_blank=True, default="")

    class Meta:
        model = Post
        fields = ("title", "slug", "body", "category", "tags", "status")

    def validate_slug(self, value: str) -> str:
        if value:
            return value
        title = str(self.initial_data.get("title", ""))
        base_slug = slugify(title)[:MAX_SLUG_LENGTH]
        if not base_slug:
            raise serializers.ValidationError(_("Slug is required."))
        return base_slug

    def _unique_slug(self, base_slug: str) -> str:
        slug_value = base_slug
        suffix = 1
        qs: QuerySet[Post] = Post.objects.all()
        instance: Post | None = getattr(self, "instance", None)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)

        while qs.filter(slug=slug_value).exists():
            candidate = f"{base_slug}-{suffix}"
            slug_value = candidate[:MAX_SLUG_LENGTH]
            suffix += 1
        return slug_value

    def create(self, validated_data: dict) -> Post:
        base_slug = validated_data.pop("slug")
        tags = validated_data.pop("tags", [])
        validated_data["slug"] = self._unique_slug(base_slug)
        post = Post.objects.create(**validated_data)
        if tags:
            post.tags.set(tags)
        logger.debug("Post created via serializer: %s", post.slug)
        return post

    def update(self, instance: Post, validated_data: dict) -> Post:
        if "slug" in validated_data:
            base_slug = validated_data["slug"]
            if base_slug:
                validated_data["slug"] = self._unique_slug(base_slug)
            else:
                validated_data["slug"] = instance.slug
        tags = validated_data.pop("tags", None)
        post = super().update(instance, validated_data)
        if tags is not None:
            post.tags.set(tags)
        logger.debug("Post updated via serializer: %s", post.slug)
        return post


class CommentReadSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "created_at")

    def get_author(self, obj: Comment) -> dict:
        return {"id": obj.author_id, "email": obj.author.email}


class CommentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("body",)
