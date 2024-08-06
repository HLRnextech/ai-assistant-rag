import threading
import traceback
import json
import time
import warnings
import uuid

import amqpstorm
import sentry_sdk
from amqpstorm import Message

from envs import (
    INPUT_QUEUE_NAME,
    MAX_URLS_ALLOWED,
    OUTPUT_QUEUE_NAME,
    RABBITMQ_URL,
    ENV,
    SENTRY_DSN
)
from db import db
from helpers.schema import InputMessageSchema
from helpers.sitemap import get_sitemap_url, scrape_sitemap
from logger import logger, set_prefix
from helpers.capture_exception import capture_exception

sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=ENV
)
warnings.filterwarnings("ignore")
connection = amqpstorm.UriConnection(RABBITMQ_URL)
channel = connection.channel()

channel.queue.declare(queue=INPUT_QUEUE_NAME, durable=True)
channel.queue.declare(queue=OUTPUT_QUEUE_NAME, durable=True)


def send_message_to_output_queue(bot_id: int, asset_id: int):
    output_msg = json.dumps({
        "bot_id": bot_id,
        "asset_id": asset_id
    })

    message = Message.create(channel, output_msg, properties={
        'delivery_mode': 2
    })

    message.publish(OUTPUT_QUEUE_NAME)


def handle_message(message):
    try:
        input_msg = message.body
        logger.info(f"Received message: {input_msg}")
        # parse and validate the msg
        parsed_msg = InputMessageSchema().loads(input_msg)
    except Exception as e:
        capture_exception(e, metadata={"input_msg": input_msg})
        traceback.print_exc()
        message.ack()
        return

    bot_id = parsed_msg['bot_id']
    asset_id = parsed_msg['asset_id']
    set_prefix(logger, f"bot_id={bot_id}, asset_id={asset_id}")
    try:
        # If the bot status is `FAILED`, do not process the asset.
        bot_data = db.query(
            f"SELECT status from public.bot where id = {bot_id} LIMIT 1;")

        if bot_data.empty:
            raise Exception(f"Bot with id {bot_id} not found")

        bot_data = bot_data.iloc[0]
        if bot_data["status"] == "FAILED":
            raise Exception(
                f"Bot with id {bot_id} is FAILED. Skipping processing of asset {asset_id}")

        # Get all assets for the bot from the db.
        bot_assets = db.query(f"""
                              SELECT a.id, a.status, a.type, a.value, a.parent_asset_id
                              FROM public.asset a
                              WHERE a.id IN (
                                SELECT ba.asset_id
                                FROM public.bot_assets ba
                                WHERE ba.bot_id = {bot_id} AND ba.deleted_at IS NULL
                              );""")

        # If any top level asset asset (no parent_asset_id) is in `FAILED` state, update the bot status to `FAILED` and do not process this asset.
        # we want to exclude parent_asset_id from this check because currently, those assets belong to a sitemap (practice url)
        # and sitemap urls can have upto 75% failure rate and be attempted at least once before marking the sitemap asset as failed
        if not bot_assets[(bot_assets["status"] == "FAILED") & (bot_assets["parent_asset_id"].isnull())].empty:
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
            raise Exception(
                f"Bot with id {bot_id} has some failed top level assets. Skipping processing of asset {asset_id}")

        # Check the asset status from the db. If the status is `pending`, it processes the asset.
        asset_data = bot_assets[bot_assets["id"] == asset_id]
        if asset_data.empty:
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
            logger.error(
                f"Bot with id {bot_id} is FAILED because asset with id {asset_id} not found")
            raise Exception(f"Asset with id {asset_id} not found")

        asset_data = asset_data.iloc[0]
        if asset_data["status"] != "PENDING":
            raise Exception(
                f"Asset with id {asset_id} is not PENDING. Skipping processing of asset {asset_id}")

        logger.info("Processing asset")

        if asset_data["type"] != "practice_url":
            logger.info(f"not processing asset of type {asset_data['type']}")
            return

        if bot_data["status"] == "QUEUED":
            db.execute(
                f"UPDATE public.bot SET status = 'PROGRESS' WHERE id = {bot_id};")
            logger.info(f"Bot is in PROGRESS now")

        sitemap_url = get_sitemap_url(asset_data["value"], logger)
        logger.info(
            f"Sitemap for practice url {asset_data['value']} is {sitemap_url}")

        if sitemap_url is None:
            # mark the asset as failed in the db
            db.execute(
                f"UPDATE public.asset SET status = 'FAILED' WHERE id = {asset_id};")
            # mark the bot as failed in the db
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
            raise Exception(
                f"Failed to find sitemap url for practice url {asset_data['value']}. Marking the asset and bot as FAILED.")

        urls = scrape_sitemap(sitemap_url)

        if len(urls) == 0:
            logger.info(f"No urls found in the sitemap {sitemap_url}")
            # mark the asset as failed in the db
            db.execute(
                f"UPDATE public.asset SET status = 'FAILED' WHERE id = {asset_id};")
            # mark the bot as failed in the db
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
            return

        if len(urls) > MAX_URLS_ALLOWED:
            urls = urls[:MAX_URLS_ALLOWED]

        try:
            with db.connection:
                with db.connection.cursor() as cur:
                    asset_ids = []
                    for url in urls:
                        url = url.replace("'", "''")
                        cur.execute(
                            f"INSERT INTO public.asset (guid, type, value, status, parent_asset_id) VALUES ('{str(uuid.uuid4().hex)}', 'url', '{url}', 'PENDING', {asset_id}) RETURNING id;")
                        id = cur.fetchone()[0]
                        asset_ids.append(id)

                    for asset_id in asset_ids:
                        cur.execute(
                            f"INSERT INTO public.bot_assets (bot_id, asset_id) VALUES ({bot_id}, {asset_id});")
        except Exception as e:
            capture_exception(
                e, metadata={"bot_id": bot_id, "asset_id": asset_id})
            traceback.print_exc()
            logger.error(
                "Failed to create assets for the sitemap. Marking the asset and bot as FAILED.")
            db.execute(
                f"UPDATE public.asset SET status = 'FAILED' WHERE id = {asset_id};")
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
            return

        logger.info(
            f"Successfully created {len(urls)} assets for the sitemap {sitemap_url}")

        for asset_id in asset_ids:
            send_message_to_output_queue(bot_id, asset_id)

    except Exception as e:
        capture_exception(e, metadata={"bot_id": bot_id, "asset_id": asset_id})
        traceback.print_exc()
        logger.error("Failed to process the asset")
    finally:
        message.ack()


def heartbeat():
    while True:
        connection.heartbeat.send_heartbeat_impl()
        time.sleep(10)


def main():
    try:
        logger.info("Starting service")
        channel.basic.qos(prefetch_count=1)
        channel.basic.consume(
            handle_message, queue=INPUT_QUEUE_NAME, no_ack=False)

        logger.info(f'waiting for messages on {INPUT_QUEUE_NAME}')

        # start a daemon thread to call connection.process_data_events() every 10s
        # to prevent the connection from closing
        threading.Thread(target=heartbeat, daemon=True).start()

        channel.start_consuming()
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
    finally:
        channel.close()
        connection.close()
