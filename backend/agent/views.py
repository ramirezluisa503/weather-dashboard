from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Conversation
from .serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
    QuestionSerializer,
)


class ConversationListCreateView(generics.ListCreateAPIView):
    """GET: lista de conversaciones (la más reciente primero) · POST: crea una conversación vacía."""

    authentication_classes = []  # API sin sesiones ni cookies: no aplica CSRF
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer


class ConversationDetailView(generics.RetrieveAPIView):
    """GET: una conversación con sus mensajes y las tools que usó el agente."""

    authentication_classes = []
    # Evita el problema N+1: trae mensajes y tool calls en pocas consultas
    queryset = Conversation.objects.prefetch_related("messages__tool_calls")
    serializer_class = ConversationDetailSerializer


class AskView(APIView):
    """POST: envía una pregunta al agente y devuelve su respuesta con la evidencia (tools usadas)."""

    authentication_classes = []
    throttle_scope = "agent"  # máximo de preguntas por minuto (protege el cupo del LLM)

    @extend_schema(request=QuestionSerializer, responses={201: MessageSerializer})
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        question = QuestionSerializer(data=request.data)
        question.is_valid(raise_exception=True)

        answer = services.ask(conversation, question.validated_data["content"])
        return Response(MessageSerializer(answer).data, status=status.HTTP_201_CREATED)
