import { useCallback, useEffect, useState } from 'react';
import {
  askQuestion,
  createConversation,
  getConversation,
  listConversations,
} from '../api/chatApi';

// Estado y acciones del chat: conversaciones, mensajes, "pensando" y errores
export default function useChat() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState(null);

  const refreshConversations = useCallback(() => {
    listConversations()
      .then(setConversations)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const openConversation = useCallback(async (id) => {
    setActiveId(id);
    setError(null);
    try {
      const conversation = await getConversation(id);
      setMessages(conversation.messages);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // La conversación nueva se crea en el backend recién con la primera pregunta (no quedan vacías)
  const startConversation = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }, []);

  // Devuelve true si el agente respondió; false si hubo un error (para devolver el texto al input)
  const sendMessage = useCallback(
    async (text) => {
      const tempId = `tmp-${Date.now()}`;
      setError(null);
      // Actualización optimista: la pregunta aparece de inmediato, antes de que responda el servidor
      setMessages((previous) => [...previous, { id: tempId, role: 'user', content: text, tool_calls: [] }]);
      setThinking(true);

      try {
        let conversationId = activeId;
        if (!conversationId) {
          conversationId = (await createConversation()).id;
          setActiveId(conversationId);
        }
        const answer = await askQuestion(conversationId, text);
        setMessages((previous) => [...previous, answer]);
        refreshConversations(); // la conversación nueva (o actualizada) sube en la lista
        return true;
      } catch (err) {
        setMessages((previous) => previous.filter((message) => message.id !== tempId));
        setError(err.message);
        return false;
      } finally {
        setThinking(false);
      }
    },
    [activeId, refreshConversations],
  );

  return { conversations, activeId, messages, thinking, error, openConversation, startConversation, sendMessage };
}
