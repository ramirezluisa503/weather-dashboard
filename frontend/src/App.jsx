import { useCallback, useState } from 'react';
import { Alert, Spin, message } from 'antd';
import Background from './components/Background';
import CitySelector from './components/CitySelector';
import ComparisonChart from './components/ComparisonChart';
import HistoryTable from './components/HistoryTable';
import Navbar from './components/Navbar';
import WeatherCard from './components/WeatherCard';
import useDashboard from './hooks/useDashboard';
import useWeatherSocket from './hooks/useWeatherSocket';
import { getTemperatureTheme } from './utils/weatherTheme';

export default function App() {
  const [view, setView] = useState('comparison');
  const [cities, setCities] = useState({ city1: 'Bogota', city2: 'Medellin' });
  const { data, error, loading, reload } = useDashboard(cities.city1, cities.city2);
  const [historyVersion, setHistoryVersion] = useState(0);
  // top: 90 → las notificaciones aparecen debajo de la navbar fija, sin taparla
  const [messageApi, messageContext] = message.useMessage({ top: 90 });

  // Qué hacer cuando el backend avisa por WebSocket que se guardó un dato nuevo
  const handleSocketEvent = useCallback(
    (event) => {
      if (event.event !== 'weather_created') return;
      const { weather } = event;

      // La tabla siempre se actualiza (muestra todas las ciudades)
      setHistoryVersion((version) => version + 1);

      // El dashboard solo si la ciudad del aviso es una de las que se están comparando
      const selected = [cities.city1, cities.city2].map((city) => city.toLowerCase());
      if (selected.includes(weather.city.toLowerCase())) reload();

      messageApi.info(`Nuevo dato: ${weather.city} · ${weather.temperature.toFixed(1)} °C`);
    },
    [cities, reload, messageApi],
  );

  const socketStatus = useWeatherSocket(handleSocketEvent);

  // Cada mitad del fondo usa el tema de SU ciudad (mientras carga, el tema templado)
  const defaultTheme = getTemperatureTheme(15);
  const [firstTheme, secondTheme] = data
    ? data.cities.map((city) => getTemperatureTheme(city.current.temperature))
    : [defaultTheme, defaultTheme];

  return (
    <>
      {messageContext}
      <Background firstImage={firstTheme.image} secondImage={secondTheme.image} />
      <main className="app">
        <Navbar view={view} onViewChange={setView} socketStatus={socketStatus} />

        {/* Las vistas se OCULTAN (hidden) en vez de desmontarse: así conservan su estado
            (por ejemplo, el filtro y la página de la tabla) al cambiar de pestaña */}
        <div className="view" hidden={view !== 'comparison'}>
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
            <>
              <section className={loading ? 'cards is-loading' : 'cards'}>
                {data.cities.map((city) => (
                  <WeatherCard key={city.city} weather={city.current} />
                ))}
              </section>
              <ComparisonChart cities={data.cities} />
            </>
          )}
        </div>

        {/* La tabla es independiente del dashboard: tiene su propio filtro y sus propios datos */}
        <div className="view" hidden={view !== 'history'}>
          <HistoryTable refreshKey={historyVersion} />
        </div>
      </main>
    </>
  );
}
