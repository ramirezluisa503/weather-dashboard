from django.db import models


class Conversation(models.Model):
    """Una conversación del chat con el agente."""

    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversación {self.pk}"


class Message(models.Model):
    """Un mensaje de la conversación: de la usuaria o del asistente."""

    class Role(models.TextChoices):
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    is_error = models.BooleanField(default=False, help_text="True si el agente no pudo responder")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class ToolCall(models.Model):
    """Registro de una tool que el agente ejecutó para responder un mensaje (evidencia)."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="tool_calls")
    name = models.CharField(max_length=50)
    arguments = models.JSONField(default=dict)
    result = models.JSONField(default=dict, help_text="Salida saneada y resumida de la tool")
    is_error = models.BooleanField(default=False)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name}({self.arguments})"