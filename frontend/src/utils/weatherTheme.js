// Cada tema define la foto y los colores según la temperatura (°C).
// Se elige el primer tema cuya temperatura máxima sea mayor que la de la ciudad.
export const TEMPERATURE_THEMES = [
  {
    key: 'cold',
    label: 'Frío',
    maxTemp: 12,
    image: '/images/cold.webp',
    accent: '#7dd3fc',
  },
  {
    key: 'mild',
    label: 'Templado',
    maxTemp: 20,
    image: '/images/mild.webp',
    accent: '#86efac',
  },
  {
    key: 'warm',
    label: 'Cálido',
    maxTemp: 28,
    image: '/images/warm.webp',
    accent: '#fcd34d',
  },
  {
    key: 'hot',
    label: 'Caluroso',
    maxTemp: Infinity,
    image: '/images/hot.webp',
    accent: '#fb923c',
  },
];

export function getTemperatureTheme(temperature) {
  return (
    TEMPERATURE_THEMES.find((theme) => temperature < theme.maxTemp) ??
    TEMPERATURE_THEMES[TEMPERATURE_THEMES.length - 1]
  );
}
