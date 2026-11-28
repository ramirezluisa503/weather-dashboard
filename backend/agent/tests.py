"""Tests del agente (Parte B).

- Las tools se prueban contra una base de datos de prueba con datos conocidos (resultados exactos).
- El LLM se SIMULA con unittest.mock: los tests no gastan cupo de Gemini, no dependen de internet
  y siempre dan el mismo resultado. Se prueba NUESTRO código: el ciclo, las tools, los errores.

Ejecutar:  docker compose exec backend python manage.py test agent -v 2
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import litellm
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from weather.models import WeatherData

from . import services
from .models import Conversation, Message, ToolCall
from .tools import run_tool

# Caché en memoria (el límite de peticiones la usa): los tests no dependen de Redis
TEST_SETTINGS = override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)

# Dónde "interceptamos" la llamada al LLM (el nombre tal como lo usa services.py)
CALL_LLM = "agent.services._call_llm"


def create_weather(city, temperature, humidity, day):
    return WeatherData.objects.create(
        city=city,
        temperature=temperature,
        humidity=humidity,
        wind_speed=2.0,
        timestamp=datetime(2026, 11, day, 12, 0, tzinfo=timezone.utc),
    )


def llm_answer(text):
    """Respuesta falsa del LLM: texto final, sin pedir tools."""
    return SimpleNamespace(content=text, tool_calls=None)


def llm_asks_tool(name, arguments, call_id="call-1"):
    """Respuesta falsa del LLM: pide ejecutar una tool."""
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id=call_id, function=function)])


class ToolTests(TestCase):
    """Las tools calculan en la BD y validan los argumentos que propone el LLM."""

    @classmethod
    def setUpTestData(cls):
        create_weather("Bogota", 10, 60, day=24)
        create_weather("Bogota", 20, 80, day=25)
        create_weather("Bogota", 30, 100, day=26)
        create_weather("Medellin", 25, 70, day=26)

    def test_promedio_calculado_en_la_bd(self):
        result, is_error = run_tool(
            "calcular_estadistica", {"ciudad": "Bogota", "metrica": "temperatura", "operacion": "promedio"}
        )
        self.assertFalse(is_error)
        self.assertEqual(result["valor"], 20.0)
        self.assertEqual(result["unidad"], "°C")
        self.assertEqual(result["registros_usados"], 3)  # evidencia: cuántos registros se usaron

    def test_normaliza_la_ciudad(self):
        result, _ = run_tool(
            "calcular_estadistica", {"ciudad": "  bogota ", "metrica": "humedad", "operacion": "maximo"}
        )
        self.assertEqual(result["filtros"]["ciudad"], "Bogota")
        self.assertEqual(result["valor"], 100)

    def test_filtra_por_rango_de_fechas(self):
        result, _ = run_tool(
            "calcular_estadistica",
            {"ciudad": "Bogota", "metrica": "temperatura", "operacion": "minimo",
             "desde": "2026-11-25", "hasta": "2026-11-26"},
        )
        self.assertEqual(result["valor"], 20.0)  # el día 24 (10 °C) queda fuera del rango
        self.assertEqual(result["registros_usados"], 2)

    def test_ciudad_sin_datos_devuelve_cero_registros(self):
        result, is_error = run_tool(
            "calcular_estadistica", {"ciudad": "Tokio", "metrica": "temperatura", "operacion": "maximo"}
        )
        self.assertFalse(is_error)
        self.assertIsNone(result["valor"])  # base para que el agente se abstenga
        self.assertEqual(result["registros_usados"], 0)

    def test_consultar_clima_respeta_el_limite(self):
        result, is_error = run_tool("consultar_clima", {"ciudad": "Bogota", "limite": 2})
        self.assertFalse(is_error)
        self.assertEqual(result["total_registros"], 3)
        self.assertEqual(result["registros_devueltos"], 2)
        self.assertEqual(result["registros"][0]["temperature"], 30)  # la más reciente primero

    def test_rechaza_argumentos_invalidos(self):
        casos = [
            {"metrica": "presion", "operacion": "promedio"},          # métrica que no existe
            {"metrica": "temperatura", "operacion": "sumar"},         # operación que no existe
            {"metrica": "temperatura", "operacion": "promedio",
             "desde": "2026-11-26", "hasta": "2026-11-24"},           # rango al revés
            {"ciudad": "Bogota; DROP TABLE", "metrica": "temperatura", "operacion": "promedio"},
        ]
        for arguments in casos:
            with self.subTest(arguments=arguments):
                result, is_error = run_tool("calcular_estadistica", arguments)
                self.assertTrue(is_error)
                self.assertIn("error", result)

    def test_tool_inexistente(self):
        result, is_error = run_tool("borrar_todo", {})
        self.assertTrue(is_error)
        self.assertIn("no existe", result["error"])


@TEST_SETTINGS
class AgentTests(TestCase):
    """El ciclo del agente con el LLM simulado."""

    def setUp(self):
        create_weather("Bogota", 10, 60, day=24)
        create_weather("Bogota", 20, 80, day=25)
        self.conversation = Conversation.objects.create()

    @patch(CALL_LLM)
    def test_ejecuta_la_tool_y_guarda_la_evidencia(self, mock_llm):
        mock_llm.side_effect = [
            llm_asks_tool("calcular_estadistica",
                          {"ciudad": "Bogota", "metrica": "temperatura", "operacion": "promedio"}),
            llm_answer("La temperatura promedio de Bogota es 15.0 °C con 2 registros."),
        ]

        message = services.ask(self.conversation, "¿Cuál es la temperatura promedio de Bogotá?")

        self.assertFalse(message.is_error)
        self.assertIn("15.0", message.content)
        tool = ToolCall.objects.get(message=message)
        self.assertEqual(tool.name, "calcular_estadistica")
        self.assertEqual(tool.result["valor"], 15.0)  # el número lo calculó el backend, no el LLM
        self.assertFalse(tool.is_error)

        # Al LLM le llegó el resultado de la tool en la segunda vuelta
        second_call_messages = mock_llm.call_args_list[1].args[0]
        self.assertEqual(second_call_messages[-1]["role"], "tool")
        self.assertIn("15.0", second_call_messages[-1]["content"])

        # Se guardaron la pregunta y la respuesta, y la conversación tomó un título
        self.assertEqual(self.conversation.messages.count(), 2)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.title, "¿Cuál es la temperatura promedio de Bogotá?")

    @patch(CALL_LLM)
    def test_envia_el_historial_como_contexto(self, mock_llm):
        mock_llm.side_effect = [llm_answer("Primera respuesta."), llm_answer("Segunda respuesta.")]

        services.ask(self.conversation, "Primera pregunta")
        services.ask(self.conversation, "¿Y la máxima?")

        second_call_messages = mock_llm.call_args_list[1].args[0]
        contents = [m["content"] for m in second_call_messages]
        self.assertIn("Primera pregunta", contents)
        self.assertIn("Primera respuesta.", contents)

    @patch(CALL_LLM)
    def test_argumentos_invalidos_no_rompen_el_agente(self, mock_llm):
        mock_llm.side_effect = [
            llm_asks_tool("calcular_estadistica", {"metrica": "presion", "operacion": "promedio"}),
            llm_answer("No puedo calcular esa métrica."),
        ]

        message = services.ask(self.conversation, "Promedio de presión")

        self.assertFalse(message.is_error)
        self.assertTrue(ToolCall.objects.get(message=message).is_error)

    @patch(CALL_LLM)
    def test_limite_de_pasos(self, mock_llm):
        # El LLM pide tools sin parar: el agente corta a los MAX_STEPS pasos
        mock_llm.return_value = llm_asks_tool("consultar_clima", {"ciudad": "Bogota"})

        message = services.ask(self.conversation, "Pregunta que nunca termina")

        self.assertTrue(message.is_error)
        self.assertEqual(mock_llm.call_count, services.MAX_STEPS)
        self.assertEqual(ToolCall.objects.filter(message=message).count(), services.MAX_STEPS)

    @patch(CALL_LLM, side_effect=services.LLMUnavailableError)
    def test_llm_no_disponible(self, mock_llm):
        message = services.ask(self.conversation, "Hola")

        self.assertTrue(message.is_error)
        self.assertEqual(message.content, services.UNAVAILABLE_MESSAGE)

    @override_settings(LLM_MODEL="modelo-principal", LLM_FALLBACK_MODELS=["modelo-respaldo"])
    @patch("agent.services.litellm.completion")
    def test_usa_el_modelo_de_respaldo(self, mock_completion):
        saturated = litellm.exceptions.ServiceUnavailableError(
            message="503", llm_provider="gemini", model="modelo-principal"
        )
        ok = SimpleNamespace(choices=[SimpleNamespace(message=llm_answer("Respuesta del respaldo."))])
        mock_completion.side_effect = [saturated, ok]

        message = services.ask(self.conversation, "Hola")

        self.assertFalse(message.is_error)
        self.assertEqual(message.content, "Respuesta del respaldo.")
        models_used = [call.kwargs["model"] for call in mock_completion.call_args_list]
        self.assertEqual(models_used, ["modelo-principal", "modelo-respaldo"])


@TEST_SETTINGS
class ChatApiTests(TestCase):
    """Los endpoints del chat."""

    def setUp(self):
        cache.clear()  # reinicia el contador del límite de peticiones
        self.client = APIClient()
        self.conversation = Conversation.objects.create()
        self.url = f"/api/chat/conversations/{self.conversation.pk}/messages/"

    @patch(CALL_LLM, return_value=llm_answer("Hola, ¿en qué te ayudo?"))
    def test_pregunta_y_detalle(self, mock_llm):
        response = self.client.post(self.url, {"content": "Hola"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["role"], "assistant")

        detail = self.client.get(f"/api/chat/conversations/{self.conversation.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["messages"]), 2)  # el historial persiste en la BD

    def test_pregunta_vacia(self):
        response = self.client.post(self.url, {"content": "   "}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_conversacion_inexistente(self):
        response = self.client.post("/api/chat/conversations/9999/messages/", {"content": "Hola"}, format="json")
        self.assertEqual(response.status_code, 404)

    @patch(CALL_LLM, return_value=llm_answer("Respuesta."))
    def test_limite_de_peticiones(self, mock_llm):
        for _ in range(10):
            self.assertEqual(self.client.post(self.url, {"content": "Hola"}, format="json").status_code, 201)

        response = self.client.post(self.url, {"content": "Hola"}, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(mock_llm.call_count, 10)  # la petición 11 no llegó al LLM
