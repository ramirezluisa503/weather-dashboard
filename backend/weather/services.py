import logging

from django.core.cache import cache

from . import repositories
from .openweather_client import CityNotFoundError, OpenWeatherError, fetch_current_weather

logger = logging.getLogger(__name__)


class WeatherUnavailableError(Exception):
    """OpenWeather falló y tampoco hay datos guardados de esa ciudad."""


def normalize_city(city: str) -> str:
    """'  bogota ' -> 'Bogota'. Misma clave para caché, base de datos y fallback."""
    return " ".join(city.split()).title()


def _cache_key(city: str) -> str:
    return f"weather:latest:{city.lower()}"


def _to_dict(record) -> dict:
    return {
        "id": record.id,
        "city": record.city,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "wind_speed": record.wind_speed,
        "timestamp": record.timestamp.isoformat(),
    }


def get_current_weather(city: str) -> dict:
    """Clima actual de una ciudad: caché -> OpenWeather -> fallback a la base de datos."""
    city = normalize_city(city)
    key = _cache_key(city)

    # 1. Caché
    cached = cache.get(key)
    if cached is not None:
        logger.info("Cache HIT city=%s", city)
        return {**cached, "source": "cache"}
    logger.info("Cache MISS city=%s", city)

    # 2. API externa
    try:
        data = fetch_current_weather(city)
    except CityNotFoundError:
        logger.warning("Ciudad no encontrada en OpenWeather city=%s", city)
        raise
    except OpenWeatherError as exc:
        # 3. Fallback a la base de datos
        logger.warning("OpenWeather falló (%s). Fallback a la BD city=%s", exc, city)
        latest = repositories.get_latest_by_city(city)
        if latest is None:
            logger.error("Sin datos en la BD para el fallback city=%s", city)
            raise WeatherUnavailableError(f"No hay datos disponibles para {city}") from exc
        return {**_to_dict(latest), "source": "database"}

    # 4. Guardar en la BD y en la caché
    data["city"] = city
    record, created = repositories.save_weather(data)
    if created:
        logger.info("Nuevo registro id=%s city=%s", record.id, city)

    result = _to_dict(record)
    cache.set(key, result)
    return {**result, "source": "api"}