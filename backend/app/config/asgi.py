#app/config/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings")
django_asgi_app = get_asgi_application()
