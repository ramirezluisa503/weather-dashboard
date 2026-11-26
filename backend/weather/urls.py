from django.urls import path

from . import views

urlpatterns = [
    path("weather/", views.WeatherListView.as_view(), name="weather-list"),
    path("dashboard-data/", views.DashboardDataView.as_view(), name="dashboard-data"),
    path("weather/export/", views.WeatherExportCSVView.as_view(), name="weather-export"),
]