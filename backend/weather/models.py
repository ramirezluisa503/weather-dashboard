from django.db import models


class WeatherData(models.Model):
    """Registro histórico del clima de una ciudad en un momento dado."""

    city = models.CharField(max_length=100)
    temperature = models.FloatField(help_text="Temperatura en °C")
    humidity = models.PositiveSmallIntegerField(help_text="Humedad relativa en %")
    wind_speed = models.FloatField(help_text="Velocidad del viento en m/s")
    timestamp = models.DateTimeField(help_text="Momento de la medición (UTC)")
    # Estado del cielo según OpenWeather (opcionales: los registros antiguos no los tienen)
    condition = models.CharField(max_length=30, blank=True, default="", help_text="Categoría: Clear, Clouds, Rain...")
    description = models.CharField(max_length=100, blank=True, default="", help_text="Descripción en español")
    icon = models.CharField(max_length=5, blank=True, default="", help_text="Código de ícono de OpenWeather, ej. 03d")

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["city", "-timestamp"], name="weather_city_ts_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["city", "timestamp"], name="unique_city_timestamp"),
        ]

    def __str__(self):
        return f"{self.city} - {self.temperature}°C @ {self.timestamp:%Y-%m-%d %H:%M}"