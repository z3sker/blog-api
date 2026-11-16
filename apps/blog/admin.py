from typing import Any

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.sections import TableSection

from django.contrib import admin
from django.db import models
from django.db.models import Case, Count, Prefetch, QuerySet, Value, When
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from apps.blog.constants import (
    COMMENT_BODY_PREVIEW_LENGTH,
    COMMENTS_INLINE_PER_PAGE,
    SECTION_BODY_PREVIEW_LENGTH,
)
from apps.blog.models import Category, Comment, Post, Tag

STATUS_LABEL_COLORS = {
    Post.Status.PUBLISHED: "success",
    Post.Status.DRAFT: "warning",
}
POST_FILTER_PARAM = "post__id__exact"


class CategoryPostsSection(TableSection):
    verbose_name = "Posts in this category"
    related_name = "post_set"
    fields = ["title", "author", "status", "created_at"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "post_count"]
    ordering = ["name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [CategoryPostsSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .annotate(post_count=Count("post"))
            .prefetch_related(Prefetch("post_set", queryset=Post.objects.select_related("author")))
        )

    @display(description="Posts", ordering="post_count")
    def post_count(self, obj: Category) -> int:
        return obj.post_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["name", "slug", "post_count"]
    ordering = ["name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(post_count=Count("post"))

    @display(description="Posts", ordering="post_count")
    def post_count(self, obj: Tag) -> int:
        return obj.post_count


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ["post_title", "author", "short_body", "created_at"]
    list_filter = [
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    list_select_related = ["post", "author"]
    search_fields = ["body", "author__email", "post__title"]
    autocomplete_fields = ["post", "author"]
    readonly_fields = ["created_at"]

    @display(description="Post", ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Comment")
    def short_body(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_BODY_PREVIEW_LENGTH)


class CommentInline(TabularInline):
    model = Comment
    fields = ["author", "body", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["author"]
    extra = 0
    tab = True
    per_page = COMMENTS_INLINE_PER_PAGE
    show_count = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Comment]:
        return super().get_queryset(request).select_related("author")


class PostCommentsSection(TableSection):
    verbose_name = "Comments"
    related_name = "comment_set"
    fields = ["author", "short_body", "created_at"]

    @display(description="Comment")
    def short_body(self, instance: Comment) -> str:
        return Truncator(instance.body).chars(SECTION_BODY_PREVIEW_LENGTH)


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = [
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comment_count",
        "created_at",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    ordering = ["-created_at"]
    search_fields = ["title", "body", "author__email"]
    list_sections = [PostCommentsSection]

    fieldsets = (
        ("Content", {"classes": ["tab"], "fields": ("title", "slug", "body")}),
        ("Classification", {"classes": ["tab"], "fields": ("category", "tags", "status")}),
        ("Meta", {"classes": ["tab"], "fields": ("author", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["author", "category", "tags"]
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    warn_unsaved_form = True
    inlines = [CommentInline]

    actions = ["publish_selected", "move_to_drafts"]
    actions_row = ["toggle_status"]
    actions_list = ["publish_all_drafts"]
    actions_detail = ["open_comments"]
    actions_submit_line = ["save_and_publish"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related(
                "tags",
                Prefetch("comment_set", queryset=Comment.objects.select_related("author")),
            )
            .annotate(comment_count=Count("comment", distinct=True))
        )

    @display(description="Post", header=True, ordering="title")
    def post_header(self, obj: Post) -> tuple[str, str]:
        return obj.title, obj.author.email

    @display(description="Status", ordering="status", label=STATUS_LABEL_COLORS)
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict[str, Any]:
        tags = obj.tags.all()
        return {
            "title": f"{len(tags)} tags",
            "items": [{"title": tag.name} for tag in tags],
        }

    @display(description="Comments", ordering="comment_count")
    def comment_count(self, obj: Post) -> int:
        return obj.comment_count

    def update_status(self, queryset: QuerySet[Post], status: str) -> int:
        return queryset.update(status=status, updated_at=timezone.now())

    @action(description="Publish selected", permissions=["change"], icon="publish")
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = self.update_status(queryset, Post.Status.PUBLISHED)
        self.message_user(request, f"{updated} posts published.")

    @action(description="Move to drafts", permissions=["change"], icon="unpublished")
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = self.update_status(queryset, Post.Status.DRAFT)
        self.message_user(request, f"{updated} posts moved to drafts.")

    @action(
        description="Publish / unpublish",
        url_path="toggle-status",
        permissions=["change"],
        icon="swap_horiz",
    )
    def toggle_status(self, request: HttpRequest, object_id: int) -> HttpResponse:
        Post.objects.filter(pk=object_id).update(
            status=Case(
                When(status=Post.Status.DRAFT, then=Value(Post.Status.PUBLISHED)),
                default=Value(Post.Status.DRAFT),
            ),
            updated_at=timezone.now(),
        )
        self.message_user(request, "Post status changed.")
        return redirect(request.headers.get("referer") or reverse("admin:blog_post_changelist"))

    @action(
        description="Publish all drafts",
        url_path="publish-all-drafts",
        permissions=["change"],
        icon="done_all",
        variant=ActionVariant.PRIMARY,
    )
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        drafts = Post.objects.filter(status=Post.Status.DRAFT)
        updated = self.update_status(drafts, Post.Status.PUBLISHED)
        self.message_user(request, f"{updated} drafts published.")
        return redirect(reverse("admin:blog_post_changelist"))

    @action(description="Open comments", url_path="open-comments", icon="chat")
    def open_comments(self, request: HttpRequest, object_id: int) -> HttpResponseRedirect:
        url = reverse("admin:blog_comment_changelist")
        return redirect(f"{url}?{POST_FILTER_PARAM}={object_id}")

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"“{obj.title}” published.")
