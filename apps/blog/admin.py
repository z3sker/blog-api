from __future__ import annotations

from django.contrib import admin

from apps.blog.models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_ru", "name_kk", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "name_ru", "name_kk")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body", "author__email")
    filter_horizontal = ("tags",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("body", "author__email", "post__title")
