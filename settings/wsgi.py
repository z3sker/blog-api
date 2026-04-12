import os
from pathlib import Path

from decouple import AutoConfig

from django.core.wsgi import get_wsgi_application

base_dir = Path(__file__).resolve().parent.parent
config = AutoConfig(search_path=str(base_dir / "settings"))
env_id = config("BLOG_ENV_ID", default="local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{env_id}")

application = get_wsgi_application()
