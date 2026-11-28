"""Eval set del agente: hace preguntas REALES al LLM y califica las respuestas.

A diferencia de los tests (LLM simulado), aquí se mide el comportamiento del modelo de verdad:
¿usa la tool correcta?, ¿da el número que calcula la BD?, ¿se abstiene?, ¿pide aclaración?

La "respuesta esperada" de las preguntas con números se calcula en el momento con run_tool,
porque los datos crecen cada 10 minutos (Celery).

Ejecutar:  docker compose exec backend python manage.py run_evals
Consume cupo del LLM (unas 15 llamadas): no forma parte de los tests automáticos.
"""

import json
import re
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from agent import services
from agent.models import Conversation
from agent.tools import run_tool

EVAL_SET = Path(__file__).resolve().parents[2] / "evals" / "eval_set.json"
# Formas de decir "no hay datos": no hay / no tengo / no tenemos / no cuento / no encontré / sin registros…
ABSTENTION_PATTERN = re.compile(
    r"\bno (hay|tengo|tenemos|cuento|contamos|dispongo|disponemos|existen|encontr\w*)|\bsin (datos|registros)",
    re.IGNORECASE,
)


def _number_variants(value):
    """Formas aceptables de escribir un número: 14.83 → 14.83, 14,83, 14.8, 14,8 (y 15 si es entero)."""
    variants = {f"{value:.2f}", f"{value:.1f}"}
    if float(value).is_integer():
        variants.add(str(int(value)))
    return variants | {v.replace(".", ",") for v in variants}


def _mentions(answer, value):
    # Evita falsos positivos: "15" no cuenta dentro de "150" ni de "2.15"
    return any(re.search(rf"(?<![\d.,]){re.escape(v)}(?![\d])", answer) for v in _number_variants(value))


def _same_arguments(expected, used):
    """Los argumentos esperados están en los usados (la ciudad sin importar mayúsculas)."""
    return all(str(used.get(key, "")).strip().lower() == str(value).lower() for key, value in expected.items())


def _grade(case, answer, tools):
    """Devuelve la lista de verificaciones (nombre, pasó) de un caso."""
    expected = case["esperado"]
    tipo = case["tipo"]
    used = next((t for t in tools if t.name == expected.get("tool") and not t.is_error), None)

    if tipo == "estadistica":
        truth, _ = run_tool(expected["tool"], expected["argumentos"])
        return [
            ("usa la tool correcta", used is not None),
            ("argumentos correctos", used is not None and _same_arguments(expected["argumentos"], used.arguments)),
            (f"da el valor de la BD ({truth['valor']})", truth["valor"] is not None and _mentions(answer, truth["valor"])),
            (f"cita los registros ({truth['registros_usados']})", str(truth["registros_usados"]) in answer),
        ]
    if tipo == "consulta":
        truth, _ = run_tool(expected["tool"], {**expected["argumentos"], "limite": 1})
        latest = truth["registros"][0]["temperature"] if truth["registros"] else None
        return [
            ("usa la tool correcta", used is not None),
            ("argumentos correctos", used is not None and _same_arguments(expected["argumentos"], used.arguments)),
            (f"incluye la medición más reciente ({latest} °C)", latest is not None and _mentions(answer, latest)),
        ]
    if tipo == "abstencion":
        return [
            ("dice que no hay datos", ABSTENTION_PATTERN.search(answer) is not None),
            ("no inventa una temperatura", re.search(r"\d\s*°", answer) is None),
        ]
    if tipo == "aclaracion":
        return [("no usa tools", not tools), ("pregunta la ciudad", "ciudad" in answer.lower())]
    if tipo == "fuera_de_tema":
        return [("no usa tools", not tools), ("menciona el clima", "clima" in answer.lower())]
    raise ValueError(f"Tipo de caso desconocido: {tipo}")


class Command(BaseCommand):
    help = "Ejecuta el eval set del agente contra el LLM real y muestra el puntaje."

    def add_arguments(self, parser):
        parser.add_argument("--pausa", type=float, default=4, help="Segundos entre preguntas (cupo del LLM).")
        parser.add_argument("--conservar", action="store_true", help="No borrar las conversaciones de prueba.")

    def handle(self, *args, **options):
        cases = json.loads(EVAL_SET.read_text(encoding="utf-8"))
        passed_cases = 0

        for index, case in enumerate(cases):
            if index:
                time.sleep(options["pausa"])
            conversation = Conversation.objects.create(title=f"[eval] {case['pregunta']}"[:60])
            message = services.ask(conversation, case["pregunta"])
            tools = list(message.tool_calls.all())
            checks = _grade(case, message.content, tools) if not message.is_error else [("el LLM respondió", False)]
            ok = all(passed for _, passed in checks)
            passed_cases += ok

            style = self.style.SUCCESS if ok else self.style.ERROR
            self.stdout.write(style(f"\n[{'OK' if ok else 'FALLA'}] {case['id']}. {case['pregunta']}  ({case['tipo']})"))
            for name, passed in checks:
                self.stdout.write(f"    {'✔' if passed else '✘'} {name}")
            self.stdout.write(f"    Respuesta: {message.content[:200]}")

            if not options["conservar"]:
                conversation.delete()

        score = passed_cases / len(cases) * 100
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nPuntaje: {passed_cases}/{len(cases)} casos correctos ({score:.0f} %) · modelo {services.settings.LLM_MODEL}"
        ))
