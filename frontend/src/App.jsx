import { useState } from 'react';
import { Alert, Spin } from 'antd';
import Background from './components/Background';
import CitySelector from './components/CitySelector';
import Header from './components/Header';
import WeatherCard from './components/WeatherCard';
import useDashboard from './hooks/useDashboard';
import { getTemperatureTheme } from './utils/weatherTheme';

export default function App() {
  const [cities, setCities] = useState({ city1: 'Bogota', city2: 'Medellin' });
  const { data, error, loading } = useDashboard(cities.city1, cities.city2);

  // Cada mitad del fondo usa el tema de SU ciudad (mientras carga, el tema templado)
  const defaultTheme = getTemperatureTheme(15);
  const [firstTheme, secondTheme] = data
    ? data.cities.map((city) => getTemperatureTheme(city.current.temperature))
    : [defaultTheme, defaultTheme];

  return (
    <>
      <Background firstImage={firstTheme.image} secondImage={secondTheme.image} />
      <main className="app">
        <Header />

        <CitySelector
          initialCity1={cities.city1}
          initialCity2={cities.city2}
          loading={loading}
          onCompare={(city1, city2) => setCities({ city1, city2 })}
        />

        {error && (
          <Alert
            type="error"
            showIcon
            title="No se pudo cargar el clima"
            description={error}
          />
        )}

        {/* Spinner grande solo en la primera carga (todavía no hay datos) */}
        {!data && loading && (
          <div className="glass" style={{ padding: 48, textAlign: 'center' }}>
            <Spin size="large" description="Consultando el clima...">
              <div style={{ minHeight: 40 }} />
            </Spin>
          </div>
        )}

        {/* En las cargas siguientes, las tarjetas actuales se atenúan */}
        {data && (
          <section className={loading ? 'cards is-loading' : 'cards'}>
            {data.cities.map((city) => (
              <WeatherCard key={city.city} weather={city.current} />
            ))}
          </section>
        )}
      </main>
    </>
  );
}
