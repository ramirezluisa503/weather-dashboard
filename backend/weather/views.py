import csv

from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .pagination import StandardPagination
from .serializers import CityQuerySerializer, DashboardQuerySerializer, WeatherDataSerializer
from .services import CityNotFoundError, WeatherUnavailableError


class WeatherListView(generics.ListAPIView):
    """GET /api/weather/?city=&page=&page_size= : histórico paginado."""

    serializer_class = WeatherDataSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = CityQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return services.list_history(params.validated_data.get("city"))


class DashboardDataView(APIView):
    """GET /api/dashboard-data/?city1=&city2= : clima actual + histórico de dos ciudades."""

    def get(self, request):
        params = DashboardQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        try:
            data = services.get_dashboard_data(
                params.validated_data["city1"], params.validated_data["city2"]
            )
        except CityNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except WeatherUnavailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(data)


class _Echo:
    """Pseudo-archivo: csv.writer escribe aquí y recibimos cada línea ya formateada."""

    def write(self, value):
        return value


class WeatherExportCSVView(APIView):
    """GET /api/weather/export/?city= : descarga el histórico en CSV (streaming)."""

    def get(self, request):
        params = CityQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        rows = services.iter_export_rows(params.validated_data.get("city"))

        response = StreamingHttpResponse(
            self._csv_lines(rows), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = 'attachment; filename="weather_data.csv"'
        return response

    @staticmethod
    def _csv_lines(rows):
        writer = csv.writer(_Echo())
        yield "﻿"
        for row in rows:
            yield writer.writerow(row)
