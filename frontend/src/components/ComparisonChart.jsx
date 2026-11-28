import { useState } from 'react';
import { Empty, Segmented } from 'antd';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getTemperatureTheme } from '../utils/weatherTheme';

const METRICS = {
  temperature: { label: 'Temperatura', unit: '°C' },
  humidity: { label: 'Humedad', unit: '%' },
  wind_speed: { label: 'Viento', unit: 'm/s' },
};
const METRIC_OPTIONS = Object.entries(METRICS).map(([value, { label }]) => ({
  value,
  label,
}));

// Color alternativo si las dos ciudades tienen el mismo tema (mismo color de acento)
const FALLBACK_COLOR = '#7c3aed';

const timeFormatter = new Intl.DateTimeFormat('es-CO', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

// Une los históricos de las dos ciudades en una sola lista ordenada por tiempo
function buildChartData(cities, metric) {
  return cities
    .flatMap((city) =>
      city.history.map((row) => ({
        time: new Date(row.timestamp).getTime(),
        [city.city]: row[metric],
      })),
    )
    .sort((a, b) => a.time - b.time);
}

function getLineColors(cities) {
  const colors = cities.map(
    (city) => getTemperatureTheme(city.current.temperature).accent,
  );
  if (colors[0] === colors[1]) colors[1] = FALLBACK_COLOR;
  return colors;
}

export default function ComparisonChart({ cities }) {
  const [metric, setMetric] = useState('temperature');
  const { unit } = METRICS[metric];
  const data = buildChartData(cities, metric);
  const colors = getLineColors(cities);

  return (
    <section className="chart-card panel">
      <header className="chart-card__header">
        <h2>Comparación en el tiempo</h2>
        <Segmented
          value={metric}
          onChange={setMetric}
          options={METRIC_OPTIONS}
        />
      </header>

      {data.length === 0 ? (
        <Empty description="Aún no hay histórico para estas ciudades" />
      ) : (
        <ResponsiveContainer
          width="100%"
          height={320}
        >
          <LineChart
            data={data}
            margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid
              stroke="#e2e8f0"
              strokeDasharray="3 3"
            />
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(time) => timeFormatter.format(time)}
              minTickGap={24}
              stroke="#64748b"
              fontSize={12}
            />
            <YAxis
              unit={unit}
              width={64}
              stroke="#64748b"
              fontSize={12}
            />
            <Tooltip
              labelFormatter={(time) => timeFormatter.format(time)}
              formatter={(value, name) => [`${value} ${unit}`, name]}
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: 12,
                boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08)',
              }}
            />
            <Legend />
            {cities.map((city, index) => (
              <Line
                key={city.city}
                type="monotone"
                dataKey={city.city}
                name={city.city}
                stroke={colors[index]}
                strokeWidth={3}
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
