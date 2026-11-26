import csv

from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .pagination import StandardPagination
from .serializers import CityQuerySerializer, DashboardQuerySerializer, WeatherDataSerializer
from .services import CityNotFoundError, WeatherUnavailableError

# Carácter invisible (BOM) al inicio del CSV para que Excel lo abra como UTF-8 (tildes correctas)
UTF8_BOM = "\ufeff"


@extend_schema_view(
    get=extend_schema(
        summary="Histórico paginado",
        parameters=[CityQuerySerializer],
    )
)
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

    @extend_schema(
        summary="Datos del dashboard para dos ciudades",
        parameters=[DashboardQuerySerializer],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiResponse(description="Parámetros inválidos"),
            404: OpenApiResponse(description="Ciudad no encontrada"),
            503: OpenApiResponse(description="OpenWeather no disponible y sin datos guardados"),
        },
    )
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

    @extend_schema(
        summary="Exportar histórico en CSV",
        parameters=[CityQuerySerializer],
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
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
        yield UTF8_BOM
        for row in rows:
            yield writer.writerow(row)
