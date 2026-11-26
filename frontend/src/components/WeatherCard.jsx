import { Tag } from 'antd';
import { getTemperatureTheme } from '../utils/weatherTheme';

// Formatea las fechas en español y en la hora local del navegador (el backend guarda en UTC)
const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

export default function WeatherCard({ weather }) {
  const theme = getTemperatureTheme(weather.temperature);

  return (
    <article
      className="weather-card glass"
      style={{ '--accent': theme.accent }}
    >
      <header className="weather-card__header">
        <h2 className="weather-card__city">{weather.city}</h2>
        <span className="theme-pill">{theme.label}</span>
      </header>

      <p className="weather-card__temp">{weather.temperature.toFixed(1)}°C</p>

      <div className="weather-card__metrics">
        <div className="metric">
          <span className="metric__icon">💧</span>
          <span className="metric__value">{weather.humidity}%</span>
          <span className="metric__label">Humedad</span>
        </div>
        <div className="metric">
          <span className="metric__icon">🌬️</span>
          <span className="metric__value">
            {weather.wind_speed.toFixed(1)} m/s
          </span>
          <span className="metric__label">Viento</span>
        </div>
      </div>

      <footer className="weather-card__footer">
        <span>Medición: {dateFormatter.format(new Date(weather.timestamp))}</span>
        {weather.source === 'database' && (
          <Tag color="warning">Datos guardados · OpenWeather no disponible</Tag>
        )}
      </footer>
    </article>
  );
}
