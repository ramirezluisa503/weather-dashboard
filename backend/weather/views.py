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