"""Tests de los puntos críticos del backend.

- OpenWeather se SIMULA con unittest.mock: los tests no dependen de internet ni de la cuota
  de la API y siempre dan el mismo resultado.
- Django crea una base de datos de prueba vacía y la borra al terminar (los datos reales no se tocan).
- Caché y channel layer en memoria: los tests no dependen de Redis.

Ejecutar:  docker compose exec backend python manage.py test weather -v 2
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from . import services
from .models import WeatherData
from .openweather_client import CityNotFoundError, OpenWeatherError
from .repositories import save_weather

# En los tests no dependemos de Redis: caché y channel layer en memoria
TEST_SETTINGS = override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)

# Dónde "interceptamos" la llamada a OpenWeather (el nombre tal como lo usa services.py)
FETCH = "weather.services.fetch_current_weather"
BASE_TIME = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


def fake_weather(city, temperature=20.0, minutes=0):
    """Respuesta falsa de OpenWeather, ya con los campos del modelo."""
    return {
        "city": city,
        "temperature": temperature,
        "humidity": 70,
        "wind_speed": 3.0,
        "timestamp": BASE_TIME + timedelta(minutes=minutes),
    }


@TEST_SETTINGS
class WeatherServiceTests(TestCase):
    """Lógica del servicio: caché, fallback y deduplicación."""

    def setUp(self):
        cache.clear()  # cada test empieza con la caché vacía

    def test_segunda_consulta_sale_de_la_cache(self):
        with patch(FETCH, return_value=fake_weather("Bogota")) as fetch:
            first = services.get_current_weather("bogota")
            second = services.get_current_weather("  BOGOTA ")  # misma ciudad, escrita distinto

        self.assertEqual(first["source"], "api")
        self.assertEqual(second["source"], "cache")
        fetch.assert_called_once()  # OpenWeather se llamó UNA sola vez

    def test_fallback_a_la_bd_si_openweather_falla(self):
        save_weather(fake_weather("Bogota", temperature=15.5))

        with patch(FETCH, side_effect=OpenWeatherError("caída simulada")):
            result = services.get_current_weather("bogota")

        self.assertEqual(result["source"], "database")
        self.assertEqual(result["temperature"], 15.5)

    def test_sin_datos_y_api_caida_lanza_error(self):
        with patch(FETCH, side_effect=OpenWeatherError("caída simulada")):
            with self.assertRaises(services.WeatherUnavailableError):
                services.get_current_weather("Cali")

    def test_misma_medicion_no_se_duplica(self):
        data = fake_weather("Bogota")
        _, created_first = save_weather(data)
        _, created_second = save_weather(data)

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(WeatherData.objects.count(), 1)


@TEST_SETTINGS
class DashboardEndpointTests(TransactionTestCase):
    """/api/dashboard-data/

    Usa TransactionTestCase porque el endpoint consulta las dos ciudades en HILOS, y cada hilo
    abre su propia conexión a la BD: no vería los datos de la transacción que usa TestCase.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_devuelve_las_dos_ciudades_en_orden(self):
        with patch(FETCH, side_effect=lambda city: fake_weather(city)):
            response = self.client.get("/api/dashboard-data/?city1=medellin&city2=bogota")

        self.assertEqual(response.status_code, 200)
        cities = [item["city"] for item in response.json()["cities"]]
        self.assertEqual(cities, ["Medellin", "Bogota"])

    def test_ciudad_inexistente_responde_404(self):
        def fetch(city):
            if city == "Ciudadfalsa":
                raise CityNotFoundError(f"Ciudad no encontrada: {city}")
            return fake_weather(city)

        with patch(FETCH, side_effect=fetch):
            response = self.client.get("/api/dashboard-data/?city1=bogota&city2=ciudadfalsa")

        self.assertEqual(response.status_code, 404)

    def test_api_caida_sin_datos_responde_503(self):
        with patch(FETCH, side_effect=OpenWeatherError("caída simulada")):
            response = self.client.get("/api/dashboard-data/?city1=bogota&city2=medellin")

        self.assertEqual(response.status_code, 503)

    def test_misma_ciudad_responde_400(self):
        response = self.client.get("/api/dashboard-data/?city1=bogota&city2=BOGOTA")
        self.assertEqual(response.status_code, 400)


@TEST_SETTINGS
class HistoryEndpointTests(TestCase):
    """/api/weather/ (paginación y filtro) y /api/weather/export/ (CSV)."""

    @classmethod
    def setUpTestData(cls):
        # 15 mediciones de Bogota (una por minuto) + 1 de Medellin = 16 registros
        for minute in range(15):
            save_weather(fake_weather("Bogota", minutes=minute))
        save_weather(fake_weather("Medellin"))

    def test_paginacion_del_backend(self):
        page_1 = self.client.get("/api/weather/?page=1&page_size=10").json()
        page_2 = self.client.get("/api/weather/?page=2&page_size=10").json()

        self.assertEqual(page_1["count"], 16)
        self.assertEqual(len(page_1["results"]), 10)
        self.assertIsNotNone(page_1["next"])
        self.assertEqual(len(page_2["results"]), 6)

    def test_filtro_por_ciudad_normalizada(self):
        data = self.client.get("/api/weather/?city=medellin").json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["city"], "Medellin")

    def test_ciudad_con_caracteres_invalidos_responde_400(self):
        response = self.client.get("/api/weather/", {"city": "<script>"})
        self.assertEqual(response.status_code, 400)

    def test_exporta_csv_filtrado(self):
        response = self.client.get("/api/weather/export/?city=medellin")
        content = b"".join(response.streaming_content).decode("utf-8-sig")  # utf-8-sig quita el BOM
        lines = content.strip().splitlines()

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertEqual(lines[0], "id,city,temperature,humidity,wind_speed,timestamp")
        self.assertEqual(len(lines), 2)  # encabezado + 1 fila de Medellin
