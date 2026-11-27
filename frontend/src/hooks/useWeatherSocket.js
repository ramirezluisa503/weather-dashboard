import { useEffect, useRef, useState } from 'react';
import { WS_URL } from '../api/weatherApi';

const MAX_RETRY_DELAY_MS = 30000;

// Mantiene abierta la conexión WebSocket, se reconecta sola (backoff exponencial)
// y avisa cada evento recibido. Devuelve el estado: 'connecting' | 'open' | 'reconnecting'
export default function useWeatherSocket(onEvent) {
  const [status, setStatus] = useState('connecting');
  const onEventRef = useRef(onEvent);

  // Siempre usar la versión más reciente de onEvent sin reiniciar la conexión
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let socket;
    let retries = 0;
    let retryTimer;
    let stopped = false;

    const connect = () => {
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        retries = 0;
        setStatus('open');
      };

      socket.onmessage = (message) => {
        try {
          onEventRef.current?.(JSON.parse(message.data));
        } catch {
          // Mensaje con formato inesperado: se ignora
        }
      };

      socket.onclose = () => {
        if (stopped) return;
        setStatus('reconnecting');
        const delay = Math.min(1000 * 2 ** retries, MAX_RETRY_DELAY_MS);
        retries += 1;
        retryTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => socket.close();
    };

    connect();

    // Limpieza: cierre intencional (no es una caída), así que no se reintenta
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return status;
}
