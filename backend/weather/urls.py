from django.urls import path

from . import views

urlpatterns = [
    path("weather/", views.WeatherListView.as_view(), name="weather-list"),
]