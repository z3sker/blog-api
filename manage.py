#!/usr/bin/env python
import os
import sys
from pathlib import Path

from decouple import AutoConfig


def main():
    base_dir = Path(__file__).resolve().parent
    config = AutoConfig(search_path=str(base_dir / "settings"))
    env_id = config("BLOG_ENV_ID", default="local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{env_id}")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
