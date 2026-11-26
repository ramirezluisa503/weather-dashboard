from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/weather/", consumers.WeatherConsumer.as_asgi()),
]