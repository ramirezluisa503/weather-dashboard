"""Tools tipadas del agente: el LLM solo propone argumentos; el backend los valida y consulta la BD.

Sin SQL arbitrario, sin shell y sin URLs: cada tool acepta solo parámetros cerrados y validados.
"""
from datetime import datetime, time, timezone

from django.db.models import Avg, Count, Max, Min
from rest_framework import serializers

from weather.repositories import filter_weather
from weather.serializers import validate_city_name
from weather.services import normalize_city

METRICAS = {
    "temperatura": ("temperature", "°C"),
    "humedad": ("humidity", "%"),
    "viento": ("wind_speed", "m/s"),
}
OPERACIONES = {"promedio": Avg, "minimo": Min, "maximo": Max}
MAX_FILAS = 50


# ===== Validación de argumentos (el backend es la autoridad, no el LLM) =====
class _FiltrosArgs(serializers.Serializer):
    ciudad = serializers.CharField(required=False, max_length=100, validators=[validate_city_name])
    desde = serializers.DateField(required=False, help_text="Fecha inicial AAAA-MM-DD (UTC)")
    hasta = serializers.DateField(required=False, help_text="Fecha final AAAA-MM-DD (UTC, incluida)")

    def validate(self, attrs):
        if attrs.get("desde") and attrs.get("hasta") and attrs["desde"] > attrs["hasta"]:
            raise serializers.ValidationError("'desde' no puede ser posterior a 'hasta'.")
        return attrs


class ConsultarClimaArgs(_FiltrosArgs):
    limite = serializers.IntegerField(required=False, min_value=1, max_value=MAX_FILAS, default=10)


class CalcularEstadisticaArgs(_FiltrosArgs):
    metrica = serializers.ChoiceField(choices=list(METRICAS))
    operacion = serializers.ChoiceField(choices=list(OPERACIONES))


# ===== Ejecución =====
def _filtrar(args: dict):
    """Convierte los argumentos validados en un QuerySet y en la evidencia de los filtros usados."""
    ciudad = normalize_city(args["ciudad"]) if args.get("ciudad") else None
    inicio = datetime.combine(args["desde"], time.min, tzinfo=timezone.utc) if args.get("desde") else None
    fin = datetime.combine(args["hasta"], time.max, tzinfo=timezone.utc) if args.get("hasta") else None
    filtros = {
        "ciudad": ciudad,
        "desde": args["desde"].isoformat() if args.get("desde") else None,
        "hasta": args["hasta"].isoformat() if args.get("hasta") else None,
    }
    return filter_weather(ciudad, inicio, fin), filtros


def consultar_clima(args: dict) -> dict:
    queryset, filtros = _filtrar(args)
    total = queryset.count()
    filas = queryset.values(
        "id", "city", "temperature", "humidity", "wind_speed", "description", "timestamp"
    )[: args["limite"]]
    return {
        "filtros": filtros,
        "total_registros": total,
        "registros_devueltos": len(filas),
        "registros": [{**fila, "timestamp": fila["timestamp"].isoformat()} for fila in filas],
    }


def calcular_estadistica(args: dict) -> dict:
    queryset, filtros = _filtrar(args)
    campo, unidad = METRICAS[args["metrica"]]
    agregado = queryset.aggregate(valor=OPERACIONES[args["operacion"]](campo), registros=Count("id"))
    valor = round(agregado["valor"], 2) if agregado["valor"] is not None else None
    return {
        "filtros": filtros,
        "metrica": args["metrica"],
        "operacion": args["operacion"],
        "valor": valor,
        "unidad": unidad,
        "registros_usados": agregado["registros"],
    }


# ===== Registro: nombre → (validador, función) =====
TOOLS = {
    "consultar_clima": (ConsultarClimaArgs, consultar_clima),
    "calcular_estadistica": (CalcularEstadisticaArgs, calcular_estadistica),
}


def run_tool(name: str, arguments: dict) -> tuple[dict, bool]:
    """Valida y ejecuta una tool. Devuelve (resultado, es_error). Nunca lanza excepciones."""
    if name not in TOOLS:
        return {"error": f"La tool '{name}' no existe."}, True

    validator_class, function = TOOLS[name]
    validator = validator_class(data=arguments or {})
    if not validator.is_valid():
        return {"error": "Argumentos inválidos", "detalles": validator.errors}, True

    return function(validator.validated_data), False


# ===== Esquemas para el LLM (formato de tools de OpenAI, que LiteLLM traduce a Gemini) =====
_FILTROS_SCHEMA = {
    "ciudad": {"type": "string", "description": "Nombre de la ciudad, por ejemplo 'Bogota'."},
    "desde": {"type": "string", "description": "Fecha inicial en formato AAAA-MM-DD (UTC)."},
    "hasta": {"type": "string", "description": "Fecha final en formato AAAA-MM-DD (UTC), incluida."},
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_clima",
            "description": (
                "Devuelve mediciones guardadas del clima (más recientes primero), filtradas por "
                "ciudad y/o rango de fechas, con el total de registros que cumplen el filtro."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_FILTROS_SCHEMA,
                    "limite": {"type": "integer", "description": f"Máximo de filas (1 a {MAX_FILAS})."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_estadistica",
            "description": (
                "Calcula en la base de datos el promedio, mínimo o máximo de una métrica sobre las "
                "mediciones guardadas, filtradas por ciudad y/o rango de fechas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_FILTROS_SCHEMA,
                    "metrica": {"type": "string", "enum": list(METRICAS)},
                    "operacion": {"type": "string", "enum": list(OPERACIONES)},
                },
                "required": ["metrica", "operacion"],
            },
        },
    },
]