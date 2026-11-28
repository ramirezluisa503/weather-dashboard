import logging

from celery import shared_task
from django.conf import settings

from .openweather_client import OpenWeatherError
from .services import refresh_city

logger = logging.getLogger(__name__)


@shared_task
def refresh_tracked_cities() -> int:
    """Refresca el clima de las ciudades configuradas (la ejecuta Celery Beat cada 10 min)."""
    refreshed = 0
    for city in settings.WEATHER_TRACKED_CITIES:
        try:
            refresh_city(city)
            refreshed += 1
        except OpenWeatherError as exc:
            # Si una ciudad falla, se registra y se sigue con las demás
            logger.warning("No se pudo refrescar city=%s: %s", city, exc)

    logger.info("Refresco periódico: %s de %s ciudades", refreshed, len(settings.WEATHER_TRACKED_CITIES))
    return refreshed
