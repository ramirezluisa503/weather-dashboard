import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# Lee la configuración de settings.py: todas las variables que empiezan con CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")
# Busca automáticamente un archivo tasks.py en cada app (weather/tasks.py)
app.autodiscover_tasks()