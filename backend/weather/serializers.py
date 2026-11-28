import re

from rest_framework import serializers

from .models import WeatherData

# Letras (incluye tildes y ñ), espacios, guion, punto y apóstrofo. Ej: "San José", "Coeur d'Alene"
CITY_PATTERN = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' .-]+$")


def validate_city_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise serializers.ValidationError("La ciudad no puede estar vacía.")
    if not CITY_PATTERN.match(value):
        raise serializers.ValidationError(
            "La ciudad solo puede contener letras, espacios, guiones, puntos o apóstrofos."
        )
    return value


class WeatherDataSerializer(serializers.ModelSerializer):
    """Salida: convierte un registro WeatherData en JSON."""

    class Meta:
        model = WeatherData
        fields = [
            "id", "city", "temperature", "humidity", "wind_speed",
            "condition", "description", "icon", "timestamp",
        ]
        read_only_fields = fields


class CityQuerySerializer(serializers.Serializer):
    """Entrada: ?city= (opcional) para filtrar el histórico."""

    city = serializers.CharField(required=False, max_length=100, validators=[validate_city_name])


class DashboardQuerySerializer(serializers.Serializer):
    """Entrada: ?city1=...&city2=... para comparar dos ciudades."""

    city1 = serializers.CharField(max_length=100, validators=[validate_city_name])
    city2 = serializers.CharField(max_length=100, validators=[validate_city_name])

    def validate(self, attrs):
        if attrs["city1"].strip().lower() == attrs["city2"].strip().lower():
            raise serializers.ValidationError("Selecciona dos ciudades diferentes.")
        return attrs