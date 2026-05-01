from __future__ import annotations

import logging

from django.utils import formats, timezone
from rest_framework import serializers

from apps.core.i18n import DEFAULT_LANGUAGE
from apps.blog.models import Category, Comment, Post, Tag
from apps.users.serializers import UserSerializer


logger = logging.getLogger("blog")


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    name_en = serializers.CharField(source="name")

    class Meta:
        model = Category
        fields = ("id", "name", "name_en", "name_ru", "name_kk", "slug")

    def get_name(self, obj: Category) -> str:
        request = self.context.get("request")
        language = getattr(request, "active_language", DEFAULT_LANGUAGE)
        return obj.localized_name(language)

    def to_representation(self, instance: Category) -> dict[str, object]:
        data = super().to_representation(instance)
        data["name_en"] = instance.name
        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "created_at")
        read_only_fields = ("id", "post", "author", "created_at")

    def create(self, validated_data: dict[str, object]) -> Comment:
        post = validated_data.get("post")
        logger.info("Creating comment on post ID: %s", getattr(post, "id", None))
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category_detail = CategorySerializer(source="category", read_only=True)
    tags_detail = TagSerializer(source="tags", many=True, read_only=True)
    created_at_local = serializers.SerializerMethodField()
    updated_at_local = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "category_detail",
            "tags",
            "tags_detail",
            "status",
            "publish_at",
            "created_at",
            "updated_at",
            "created_at_local",
            "updated_at_local",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def get_created_at_local(self, obj: Post) -> str:
        return self.format_local_datetime(obj.created_at)

    def get_updated_at_local(self, obj: Post) -> str:
        return self.format_local_datetime(obj.updated_at)

    def format_local_datetime(self, value: object) -> str:
        local_value = timezone.localtime(value)
        return formats.date_format(local_value, format="DATETIME_FORMAT", use_l10n=True)

    def create(self, validated_data: dict[str, object]) -> Post:
        logger.info("Creating post with title: %s", validated_data.get("title"))
        return super().create(validated_data)

    def update(self, instance: Post, validated_data: dict[str, object]) -> Post:
        logger.info("Updating post slug: %s", instance.slug)
        return super().update(instance, validated_data)
