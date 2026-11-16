from django.http import HttpRequest
from django.urls import reverse

from apps.blog.constants import POST_STATUS_DRAFT, POST_STATUS_PUBLISHED, STATUS_FILTER_PARAM


def posts_changelist_url() -> str:
    return reverse("admin:blog_post_changelist")


def published_posts_link(request: HttpRequest) -> str:
    return f"{posts_changelist_url()}?{STATUS_FILTER_PARAM}={POST_STATUS_PUBLISHED}"


def draft_posts_link(request: HttpRequest) -> str:
    return f"{posts_changelist_url()}?{STATUS_FILTER_PARAM}={POST_STATUS_DRAFT}"


def is_all_posts_tab_active(request: HttpRequest) -> bool:
    return request.path == posts_changelist_url() and STATUS_FILTER_PARAM not in request.GET


def is_published_tab_active(request: HttpRequest) -> bool:
    return request.GET.get(STATUS_FILTER_PARAM) == POST_STATUS_PUBLISHED


def is_drafts_tab_active(request: HttpRequest) -> bool:
    return request.GET.get(STATUS_FILTER_PARAM) == POST_STATUS_DRAFT


def is_superuser(request: HttpRequest) -> bool:
    return request.user.is_superuser
