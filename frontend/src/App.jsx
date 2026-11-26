import { useEffect, useState } from 'react';
import { Alert, Spin } from 'antd';
import { getDashboardData } from './api/weatherApi';
import Background from './components/Background';
import Header from './components/Header';
import WeatherCard from './components/WeatherCard';
import { getTemperatureTheme } from './utils/weatherTheme';

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardData('bogota', 'medellin')
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  // El fondo usa el tema de la temperatura promedio de las dos ciudades
  const averageTemp = data
    ? data.cities.reduce((sum, city) => sum + city.current.temperature, 0) /
      data.cities.length
    : 15;
  const theme = getTemperatureTheme(averageTemp);

  return (
    <>
      <Background image={theme.image} />
      <main className="app">
        <Header />

        {error && (
          <Alert
            type="error"
            showIcon
            message="No se pudo cargar el clima"
            description={error}
          />
        )}

        {!data && !error && (
          <div className="glass" style={{ padding: 48, textAlign: 'center' }}>
            <Spin size="large" tip="Consultando el clima...">
              <div style={{ minHeight: 40 }} />
            </Spin>
          </div>
        )}

        {data && (
          <section className="cards">
            {data.cities.map((city) => (
              <WeatherCard key={city.city} weather={city.current} />
            ))}
          </section>
        )}
      </main>
    </>
  );
}
