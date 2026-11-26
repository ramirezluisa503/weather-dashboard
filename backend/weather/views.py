from rest_framework import generics

from . import services
from .pagination import StandardPagination
from .serializers import CityQuerySerializer, WeatherDataSerializer


class WeatherListView(generics.ListAPIView):
    """GET /api/weather/?city=&page=&page_size= : histórico paginado."""

    serializer_class = WeatherDataSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = CityQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return services.list_history(params.validated_data.get("city"))
