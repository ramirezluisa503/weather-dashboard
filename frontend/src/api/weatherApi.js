import { buildUrl, request } from './client';

export { WS_URL } from './client';

export const getDashboardData = (city1, city2) =>
  request('/dashboard-data/', { params: { city1, city2 } });

export const getWeatherHistory = ({ city, page, pageSize }) =>
  request('/weather/', { params: { city, page, page_size: pageSize } });

export const getExportUrl = (city) =>
  buildUrl('/weather/export/', { city }).toString();
