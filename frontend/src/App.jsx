import { useEffect, useState } from 'react';
import { getDashboardData } from './api/weatherApi';

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardData('bogota', 'medellin')
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p>Error: {error}</p>;
  if (!data) return <p>Cargando...</p>;
  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
