from channels.generic.websocket import JsonWebsocketConsumer
from .redis import get


class QueueConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.queue_id = self.scope["url_route"]["kwargs"]["queue_id"]
        self.accept()

    def receive_json(self, content):
        data = get(self.queue_id)
        if data:
            self.send_json(data)
