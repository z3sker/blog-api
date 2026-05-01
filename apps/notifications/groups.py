from __future__ import annotations

import hashlib


def post_comments_group_name(slug: str) -> str:
    digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:16]
    return f"post_comments_{digest}"
