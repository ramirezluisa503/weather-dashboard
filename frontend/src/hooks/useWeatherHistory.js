import { useCallback, useEffect, useState } from 'react';
import { getWeatherHistory } from '../api/weatherApi';

// Pide una página del histórico cada vez que cambian el filtro, la página o el tamaño de página
export default function useWeatherHistory({ city, page, pageSize }) {
  const [result, setResult] = useState({
    data: null,
    error: null,
    requestKey: null,
  });
  const [reloadCount, setReloadCount] = useState(0);

  const requestKey = `${city}|${page}|${pageSize}|${reloadCount}`;

  useEffect(() => {
    let cancelled = false;

    getWeatherHistory({ city, page, pageSize })
      .then((data) => {
        if (!cancelled) setResult({ data, error: null, requestKey });
      })
      .catch((err) => {
        if (!cancelled) {
          setResult((previous) => ({
            data: previous.data,
            error: err.message,
            requestKey,
          }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [city, page, pageSize, requestKey]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);

  return {
    rows: result.data?.results ?? [],
    total: result.data?.count ?? 0,
    error: result.error,
    loading: result.requestKey !== requestKey,
    reload,
  };
}
