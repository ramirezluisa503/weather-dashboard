// Cada tema define el color de acento según la temperatura (°C).
// Se elige el primer tema cuya temperatura máxima sea mayor que la de la ciudad.
// Tonos intensos para que se lean bien sobre fondo claro.
export const TEMPERATURE_THEMES = [
  { key: 'cold', label: 'Frío', maxTemp: 12, accent: '#0284c7' },
  { key: 'mild', label: 'Templado', maxTemp: 20, accent: '#16a34a' },
  { key: 'warm', label: 'Cálido', maxTemp: 28, accent: '#d97706' },
  { key: 'hot', label: 'Caluroso', maxTemp: Infinity, accent: '#ea580c' },
];

export function getTemperatureTheme(temperature) {
  return (
    TEMPERATURE_THEMES.find((theme) => temperature < theme.maxTemp) ??
    TEMPERATURE_THEMES[TEMPERATURE_THEMES.length - 1]
  );
}
