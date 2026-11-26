from .models import WeatherData


def save_weather(data: dict) -> tuple[WeatherData, bool]:
    """Guarda una medición. Si ya existe (misma ciudad y momento), no la duplica.

    Devuelve (registro, creado): creado=True solo si el registro es nuevo.
    """
    return WeatherData.objects.get_or_create(
        city=data["city"],
        timestamp=data["timestamp"],
        defaults={
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "wind_speed": data["wind_speed"],
        },
    )


def get_latest_by_city(city: str) -> WeatherData | None:
    """Último registro guardado de una ciudad, o None si no hay ninguno."""
    return WeatherData.objects.filter(city=city).order_by("-timestamp").first()


def list_weather(city: str | None = None):
    """Histórico (más reciente primero), opcionalmente filtrado por ciudad."""
    queryset = WeatherData.objects.all()
    if city:
        queryset = queryset.filter(city=city)
    return queryset