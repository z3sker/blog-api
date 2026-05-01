#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ENV_LOCAL = "local"
ENV_PROD = "prod"
ENV_SETTINGS = {
    ENV_LOCAL: "settings.env.local",
    ENV_PROD: "settings.env.prod",
}
ENV_ID_KEY = "BLOG_ENV_ID"


def read_env_id() -> str:
    env_file = Path(__file__).resolve().parent / "settings" / ".env"
    if not env_file.exists():
        return ENV_LOCAL

    for line in env_file.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue
        key, value = clean_line.split("=", 1)
        if key.strip() == ENV_ID_KEY:
            return value.strip().strip("'\"") or ENV_LOCAL
    return ENV_LOCAL


def main() -> None:
    env_id = os.environ.get(ENV_ID_KEY, read_env_id())
    settings_module = ENV_SETTINGS.get(env_id, ENV_SETTINGS[ENV_LOCAL])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

