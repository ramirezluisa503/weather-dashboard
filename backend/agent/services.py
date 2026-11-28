"""Servicio del agente: conversa con el LLM (vía LiteLLM) y ejecuta las tools que pide.

Grounding: las cifras salen siempre de las tools; el LLM nunca calcula ni inventa datos.
"""
import json
import logging
import time
import warnings
from datetime import datetime, timezone

import litellm
from django.conf import settings

from weather.models import WeatherData

from .models import Conversation, Message, ToolCall
from .tools import TOOL_SCHEMAS, run_tool

logger = logging.getLogger(__name__)

# LiteLLM emite avisos internos de Pydantic al reenviar los tool calls de Gemini; no afectan el resultado
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
# Evita que LiteLLM imprima su propio banner de ayuda en cada error (los errores los registramos nosotros)
litellm.suppress_debug_info = True

MAX_STEPS = 4          # vueltas máximas LLM ⇄ tools (evita ciclos infinitos)
HISTORY_LIMIT = 10     # mensajes anteriores que se envían como contexto
LLM_TIMEOUT_SECONDS = 30
MAX_STORED_ROWS = 5    # filas que se guardan por tool call (resultado "saneado")

# Errores del proveedor ante los que vale la pena probar el modelo de respaldo
RETRYABLE_ERRORS = (
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.RateLimitError,
    litellm.exceptions.Timeout,
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.InternalServerError,
)

UNAVAILABLE_MESSAGE = (
    "El asistente no está disponible en este momento (el servicio de IA está saturado o sin cupo). "
    "Intenta de nuevo en un minuto."
)


class LLMUnavailableError(Exception):
    """Ningún modelo (principal ni de respaldo) pudo responder."""


def _system_prompt() -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    cities = sorted(WeatherData.objects.values_list("city", flat=True).distinct())
    return f"""Eres el asistente del Weather Dashboard. Respondes preguntas sobre el HISTÓRICO de \
mediciones del clima guardado en la base de datos de la aplicación.

Reglas obligatorias:
1. Usa SIEMPRE las tools para obtener datos. Nunca inventes cifras ni uses tu conocimiento general del clima.
2. Para promedios, mínimos o máximos usa la tool calcular_estadistica. No hagas cálculos tú.
3. Cita la evidencia en la respuesta: ciudad, rango de fechas (o "todo el histórico") y número de registros usados.
4. Si una tool devuelve 0 registros o un valor nulo, di claramente que no hay datos guardados para ese filtro.
5. Si la pregunta no indica la ciudad, pregunta de qué ciudad antes de usar las tools (salvo que pida \
explícitamente "todas las ciudades"). Si es ambigua o falta otro dato necesario, pide una aclaración en vez de suponer.
6. Si la pregunta no trata del histórico del clima, explica amablemente que solo puedes responder sobre esos datos.
7. Las fechas de la base de datos están en UTC. Hoy es {today} (UTC). Usa el formato AAAA-MM-DD en las tools.
8. Responde en español, de forma breve y clara.

Ciudades con datos guardados: {", ".join(cities) or "ninguna todavía"}."""


def _call_llm(messages: list) -> object:
    """Llama al modelo principal y, si está saturado o sin cupo, a los de respaldo."""
    models = [settings.LLM_MODEL, *settings.LLM_FALLBACK_MODELS]
    for model in models:
        try:
            response = litellm.completion(
                model=model,
                api_key=settings.LLM_API_KEY,
                messages=messages,
                tools=TOOL_SCHEMAS,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            return response.choices[0].message
        except RETRYABLE_ERRORS as exc:
            # Solo el tipo de error: nunca se registran la API key ni la petición completa
            logger.warning("LLM no disponible (%s) model=%s; probando el siguiente", type(exc).__name__, model)
    raise LLMUnavailableError()


def _sanitize(result: dict) -> dict:
    """Resultado resumido para guardar: como máximo MAX_STORED_ROWS filas."""
    if isinstance(result.get("registros"), list) and len(result["registros"]) > MAX_STORED_ROWS:
        return {**result, "registros": result["registros"][:MAX_STORED_ROWS], "recortado": True}
    return result


def _history(conversation: Conversation) -> list[dict]:
    """Últimos mensajes de la conversación (sin los de error) como contexto para el LLM."""
    recent = conversation.messages.filter(is_error=False).order_by("-created_at")[:HISTORY_LIMIT]
    return [{"role": m.role, "content": m.content} for m in reversed(recent)]


def ask(conversation: Conversation, question: str) -> Message:
    """Procesa una pregunta: guarda el mensaje, ejecuta el ciclo LLM ⇄ tools y guarda la respuesta."""
    messages = [{"role": "system", "content": _system_prompt()}, *_history(conversation)]
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content=question)
    messages.append({"role": "user", "content": question})

    executed_tools = []
    answer, is_error = None, False

    try:
        for _ in range(MAX_STEPS):
            reply = _call_llm(messages)
            if not reply.tool_calls:
                answer = (reply.content or "").strip()
                break

            messages.append(reply)  # el LLM pidió tools: se devuelve tal cual en la conversación
            for tool_call in reply.tool_calls:
                name = tool_call.function.name
                started = time.perf_counter()
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                    result, tool_error = {"error": "Los argumentos no son JSON válido."}, True
                else:
                    result, tool_error = run_tool(name, arguments)

                executed_tools.append({
                    "name": name,
                    "arguments": arguments,
                    "result": _sanitize(result),
                    "is_error": tool_error,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        else:
            answer = "No pude completar la respuesta en el número máximo de pasos. ¿Puedes reformular la pregunta?"
            is_error = True
    except LLMUnavailableError:
        answer, is_error = UNAVAILABLE_MESSAGE, True
    except Exception:
        logger.exception("Error inesperado en el agente conversation=%s", conversation.pk)
        answer, is_error = "Ocurrió un error inesperado al procesar tu pregunta.", True

    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=answer or "No obtuve una respuesta del asistente.",
        is_error=is_error or not answer,
    )
    ToolCall.objects.bulk_create(ToolCall(message=assistant_message, **tool) for tool in executed_tools)

    if not conversation.title:
        conversation.title = question[:60]
    conversation.save()  # actualiza updated_at (la conversación sube al inicio de la lista)
    return assistant_message