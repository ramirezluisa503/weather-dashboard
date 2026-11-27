// Único lugar del frontend que conoce la URL del backend
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const WS_URL = `${API_URL.replace(/^http/, 'ws')}/ws/weather/`;

function buildUrl(path, params = {}) {
  const url = new URL(`/api${path}`, API_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value);
    }
  });
  return url;
}

function extractErrorMessage(data, status) {
  if (data?.detail) return data.detail;
  const firstError = Object.values(data ?? {})[0];
  if (Array.isArray(firstError) && firstError.length > 0) return firstError[0];
  return `Error ${status} al consultar la API`;
}

async function request(path, params) {
  const response = await fetch(buildUrl(path, params));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, response.status));
  }
  return data;
}

export const getDashboardData = (city1, city2) =>
  request('/dashboard-data/', { city1, city2 });

export const getWeatherHistory = ({ city, page, pageSize }) =>
  request('/weather/', { city, page, page_size: pageSize });

export const getExportUrl = (city) =>
  buildUrl('/weather/export/', { city }).toString();
