import json
import threading
import time
import amqpstorm
from amqpstorm import Message

from settings import RABBITMQ_URL, ASSET_PROCESSOR_QUEUE_NAME, SITEMAP_PROCESSOR_QUEUE_NAME
from utils.logger import logger


class Mq:
    connection = amqpstorm.UriConnection(RABBITMQ_URL)
    channel = connection.channel()

    def __init__(self) -> None:
        self.channel.queue.declare(
            queue=ASSET_PROCESSOR_QUEUE_NAME, durable=True)
        self.thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.thread.start()

    def begin_asset_processing(self, asset_id: int, bot_id: int, mime_type=None):
        payload = {"asset_id": asset_id, "bot_id": bot_id}
        if mime_type:
            payload['mime_type'] = mime_type
        payload = json.dumps(payload)
        message = Message.create(self.channel, payload, properties={
            'delivery_mode': 2
        })
        message.publish(ASSET_PROCESSOR_QUEUE_NAME)
        logger.info(
            f"Sent message to asset processor for asset {asset_id} and bot {bot_id}")

    def begin_practice_url_processing(self, asset_id: int, bot_id: int):
        payload = json.dumps({"asset_id": asset_id, "bot_id": bot_id})
        message = Message.create(self.channel, payload, properties={
            'delivery_mode': 2
        })
        message.publish(SITEMAP_PROCESSOR_QUEUE_NAME)
        logger.info(
            f"Sent message to asset processor for practice url {asset_id} and bot {bot_id}")

    def heartbeat(self):
        while True:
            self.connection.heartbeat.send_heartbeat_impl()
            time.sleep(10)


mq = Mq()
