import logging
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
TIMEOUT_SECONDS = 5


class OpenWeatherError(Exception):
    """OpenWeather falló: caída, timeout, error del servidor o respuesta inválida."""


class CityNotFoundError(OpenWeatherError):
    """La ciudad no existe en OpenWeather."""


def fetch_current_weather(city: str) -> dict:
    """Consulta el clima actual de una ciudad y lo devuelve con los campos del modelo."""
    if not settings.OPENWEATHER_API_KEY:
        raise OpenWeatherError("OPENWEATHER_API_KEY no está configurada")

    params = {"q": city, "units": "metric", "appid": settings.OPENWEATHER_API_KEY}

    try:
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.error("OpenWeather no responde (city=%s): %s", city, type(exc).__name__)
        raise OpenWeatherError("No se pudo conectar con OpenWeather") from exc

    if response.status_code == 404:
        raise CityNotFoundError(f"Ciudad no encontrada: {city}")
    if response.status_code != 200:
        logger.error("OpenWeather respondió %s (city=%s)", response.status_code, city)
        raise OpenWeatherError(f"OpenWeather respondió con estado {response.status_code}")

    try:
        data = response.json()
        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "timestamp": datetime.fromtimestamp(data["dt"], tz=timezone.utc),
        }
    except (ValueError, KeyError, TypeError) as exc:
        logger.error("Respuesta inesperada de OpenWeather (city=%s)", city)
        raise OpenWeatherError("Respuesta inválida de OpenWeather") from exc