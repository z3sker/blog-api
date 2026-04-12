from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        author = getattr(obj, "author", None)
        return author == request.user
