// Traduce el código de ícono de OpenWeather (estado REAL del cielo) a un emoji.
// El código tiene dos dígitos de condición + "d" (día) o "n" (noche): "01d" = despejado de día.
// Primero se busca el código exacto (para distinguir día/noche) y luego solo la condición.
const WEATHER_ICONS = {
  '01d': '☀️', // despejado (día)
  '01n': '🌙', // despejado (noche)
  '02d': '🌤️', // pocas nubes (día)
  '02n': '☁️', // pocas nubes (noche)
  '03': '☁️', // nubes dispersas
  '04': '☁️', // nublado
  '09': '🌧️', // llovizna / chubascos
  '10d': '🌦️', // lluvia con sol
  '10n': '🌧️', // lluvia (noche)
  '11': '⛈️', // tormenta
  '13': '❄️', // nieve
  '50': '🌫️', // niebla
};

export function getWeatherIcon(code) {
  if (!code) return null; // registros antiguos sin estado del cielo
  return WEATHER_ICONS[code] ?? WEATHER_ICONS[code.slice(0, 2)] ?? null;
}
