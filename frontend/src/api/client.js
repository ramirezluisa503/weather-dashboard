// Único lugar del frontend que conoce la URL del backend
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const WS_URL = `${API_URL.replace(/^http/, 'ws')}/ws/weather/`;

export function buildUrl(path, params = {}) {
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

// GET por defecto; para POST se pasa { method: 'POST', body }
export async function request(path, { params, method = 'GET', body } = {}) {
  const response = await fetch(buildUrl(path, params), {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, response.status));
  }
  return data;
}
