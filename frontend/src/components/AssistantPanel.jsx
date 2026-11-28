import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Empty, Input, Select, Spin, Tag } from 'antd';
import { PlusOutlined, SendOutlined } from '@ant-design/icons';
import useChat from '../hooks/useChat';

const SUGGESTIONS = [
  '¿Cuál es la temperatura promedio de Bogotá?',
  '¿Cuál fue la humedad máxima en Medellín?',
  'Muéstrame las últimas 5 mediciones de Cali',
  '¿Cuál fue la temperatura mínima en Pereira?',
];

// El LLM marca **negritas** con Markdown: se convierten a <strong> SIN usar HTML (seguro contra XSS)
function renderText(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={index}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  );
}

// Resumen corto de una tool: ciudad · operación · registros usados
function toolSummary(tool) {
  if (tool.is_error) return 'argumentos inválidos';
  const { arguments: args, result } = tool;
  const parts = [args.ciudad, args.operacion && `${args.operacion} de ${args.metrica}`];
  const count = result.registros_usados ?? result.total_registros;
  if (count !== undefined) parts.push(`${count} registros`);
  return parts.filter(Boolean).join(' · ');
}

function ToolCalls({ tools }) {
  if (!tools?.length) return null;
  return (
    <details className="tool-calls">
      <summary>
        🛠️ {tools.length === 1 ? '1 herramienta usada' : `${tools.length} herramientas usadas`}
      </summary>
      <ul>
        {tools.map((tool, index) => (
          <li key={index}>
            <Tag color={tool.is_error ? 'error' : 'processing'}>{tool.name}</Tag>
            <span>{toolSummary(tool)}</span>
            <pre>{JSON.stringify({ argumentos: tool.arguments, resultado: tool.result }, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function AssistantPanel() {
  const { conversations, activeId, messages, thinking, error, openConversation, startConversation, sendMessage } =
    useChat();
  const [draft, setDraft] = useState('');
  const messagesRef = useRef(null);

  // Al llegar un mensaje nuevo, baja al final de la conversación
  useEffect(() => {
    const box = messagesRef.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [messages, thinking]);

  const handleSend = async (text = draft) => {
    const question = text.trim();
    if (!question || thinking) return;
    setDraft('');
    const ok = await sendMessage(question);
    if (!ok) setDraft(question); // si falló, la pregunta vuelve al input para reintentar
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const conversationOptions = conversations.map((c) => ({ value: c.id, label: c.title || 'Sin título' }));

  return (
    <section className="assistant panel">
      {/* PC: lista de conversaciones a la izquierda */}
      <aside className="assistant__sidebar">
        <Button type="primary" icon={<PlusOutlined />} block onClick={startConversation}>
          Nueva conversación
        </Button>
        {conversations.length === 0 ? (
          <p className="assistant__hint">Aún no hay conversaciones.</p>
        ) : (
          <ul className="assistant__conversations">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button
                  type="button"
                  className={conversation.id === activeId ? 'conversation is-active' : 'conversation'}
                  onClick={() => openConversation(conversation.id)}
                  title={conversation.title}
                >
                  {conversation.title || 'Sin título'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Celular: botón y selector en lugar de la lista */}
      <div className="assistant__mobile-bar">
        <Button icon={<PlusOutlined />} onClick={startConversation} aria-label="Nueva conversación" />
        <Select
          placeholder="Conversaciones anteriores"
          value={activeId ?? undefined}
          onChange={openConversation}
          options={conversationOptions}
        />
      </div>

      <div className="assistant__chat">
        <header className="assistant__header">
          <h2>Asistente del clima</h2>
          <p>Responde con los datos guardados en la base de datos: nunca inventa cifras.</p>
        </header>

        <div className="assistant__messages" ref={messagesRef}>
          {messages.length === 0 && !thinking && (
            <div className="assistant__empty">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Pregúntame sobre el histórico del clima" />
              <div className="assistant__suggestions">
                {SUGGESTIONS.map((suggestion) => (
                  <Button key={suggestion} onClick={() => handleSend(suggestion)}>
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`chat-message chat-message--${message.role}${message.is_error ? ' chat-message--error' : ''}`}
            >
              <div className="chat-message__bubble">{renderText(message.content)}</div>
              {message.role === 'assistant' && <ToolCalls tools={message.tool_calls} />}
            </div>
          ))}

          {thinking && (
            <div className="chat-message chat-message--assistant">
              <div className="chat-message__bubble chat-message__thinking">
                <Spin size="small" /> El asistente está consultando los datos…
              </div>
            </div>
          )}
        </div>

        {error && <Alert type="error" showIcon title={error} />}

        <div className="assistant__composer">
          <Input.TextArea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta… (Enter para enviar, Shift + Enter para salto de línea)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            maxLength={1000}
            disabled={thinking}
            aria-label="Pregunta para el asistente"
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => handleSend()}
            loading={thinking}
            disabled={!draft.trim()}
          >
            Enviar
          </Button>
        </div>
      </div>
    </section>
  );
}
