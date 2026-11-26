from channels.generic.websocket import AsyncJsonWebsocketConsumer

WEATHER_GROUP = "weather_updates"


class WeatherConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket /ws/weather/: avisa a los navegadores cuando se guarda un dato nuevo."""

    async def connect(self):
        await self.channel_layer.group_add(WEATHER_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(WEATHER_GROUP, self.channel_name)

    async def weather_update(self, event):
        await self.send_json(event["data"])