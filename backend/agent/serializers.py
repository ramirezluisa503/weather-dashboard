from rest_framework import serializers

from .models import Conversation, Message, ToolCall


class ToolCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCall
        fields = ["name", "arguments", "result", "is_error", "duration_ms"]


class MessageSerializer(serializers.ModelSerializer):
    tool_calls = ToolCallSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ["id", "role", "content", "is_error", "created_at", "tool_calls"]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = [*ConversationSerializer.Meta.fields, "messages"]


class QuestionSerializer(serializers.Serializer):
    """Entrada: la pregunta de la usuaria."""

    content = serializers.CharField(max_length=1000, trim_whitespace=True)
