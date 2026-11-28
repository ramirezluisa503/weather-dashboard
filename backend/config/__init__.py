# Carga Celery al arrancar Django, para que las tareas se registren
from .celery import app as celery_app

__all__ = ("celery_app",)