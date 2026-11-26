import { useCallback, useEffect, useState } from 'react';
import { getDashboardData } from '../api/weatherApi';

// Pide los datos del dashboard cada vez que cambian las ciudades (o al llamar a reload)
export default function useDashboard(city1, city2) {
  const [result, setResult] = useState({
    data: null,
    error: null,
    requestKey: null,
  });
  const [reloadCount, setReloadCount] = useState(0);

  const requestKey = `${city1}|${city2}|${reloadCount}`;

  useEffect(() => {
    let cancelled = false;

    getDashboardData(city1, city2)
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
  }, [city1, city2, requestKey]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);

  return {
    data: result.data,
    error: result.error,
    loading: result.requestKey !== requestKey,
    reload,
  };
}
