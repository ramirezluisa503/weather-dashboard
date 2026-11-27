import logging
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.db import connection

from . import repositories
from .consumers import WEATHER_GROUP
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


def _notify_new_weather(weather: dict) -> None:
    """Avisa por WebSocket a los navegadores conectados. Si falla, no rompe la petición."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            WEATHER_GROUP,
            {"type": "weather.update", "data": {"event": "weather_created", "weather": weather}},
        )
    except Exception:
        logger.exception("No se pudo emitir el evento WebSocket city=%s", weather.get("city"))



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
    result = _to_dict(record)
    cache.set(key, result)

    # 5. Tiempo real: avisar solo si el registro es NUEVO
    if created:
        logger.info("Nuevo registro id=%s city=%s", record.id, city)
        _notify_new_weather(result)

    return {**result, "source": "api"}





def list_history(city: str | None = None):
    """Histórico (QuerySet), opcionalmente filtrado por ciudad normalizada."""
    if city:
        city = normalize_city(city)
    return repositories.list_weather(city)

HISTORY_LIMIT = 24


def _get_current_weather_in_thread(city: str) -> dict:
    """Versión para ejecutar en un hilo: cierra la conexión a la BD que ese hilo abre."""
    try:
        return get_current_weather(city)
    finally:
        connection.close()


def get_dashboard_data(city1: str, city2: str) -> dict:
    """Datos del dashboard para dos ciudades: clima actual (cards) + histórico (gráficos).

    El clima actual de las dos ciudades se consulta EN PARALELO (dos hilos): la mayor parte
    del tiempo es espera de red a OpenWeather, así que el tiempo total baja casi a la mitad.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        currents = list(executor.map(_get_current_weather_in_thread, (city1, city2)))

    cities = []
    for current in currents:
        history = repositories.get_recent_by_city(current["city"], HISTORY_LIMIT)
        cities.append({"city": current["city"], "current": current, "history": history})
    return {"cities": cities}


EXPORT_FIELDS = ["id", "city", "temperature", "humidity", "wind_speed", "timestamp"]


def iter_export_rows(city: str | None = None):
    """Genera las filas del CSV (encabezado + datos), leyendo la BD por bloques."""
    yield EXPORT_FIELDS
    rows = list_history(city).values_list(*EXPORT_FIELDS)
    for row in rows.iterator(chunk_size=1000):
        *values, timestamp = row
        yield [*values, timestamp.isoformat()]