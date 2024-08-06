import string
import math
import threading
import datetime
import os
import json
import re
import time
import warnings
import glob
import traceback

import sentry_sdk
from openai import OpenAI
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders.parsers.pdf import PDFPlumberParser
from langchain_community.document_loaders.blob_loaders import Blob
import amqpstorm
from bs4 import BeautifulSoup

from envs import (
    INPUT_QUEUE_NAME,
    OPENAI_API_KEY,
    RABBITMQ_URL,
    TMP_FOLDER_PATH,
    OPENAI_MODEL,
    OPENAI_EMBEDDING_MODEL,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    OPENAI_EMBEDDINGS_DIMS,
    PRACTICE_URL_SUCCESS_RATE,
    SENTRY_DSN,
    ENV
)
from db import db
from helpers.schema import InputMessageSchema
from helpers.utils import download_file_from_url
from helpers.scrape import scrape_url_smartproxy
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

if not os.path.exists(TMP_FOLDER_PATH):
    os.makedirs(TMP_FOLDER_PATH, exist_ok=True)


def handle_message(message):
    try:
        input_msg = message.body
        logger.info(f"Received message: {input_msg}")
        parsed_msg = InputMessageSchema().loads(input_msg)
    except Exception as e:
        capture_exception(e, metadata={"message": input_msg})
        message.ack()
        traceback.print_exc()
        return

    bot_id = parsed_msg['bot_id']
    asset_id = parsed_msg['asset_id']
    mime_type = parsed_msg.get('mime_type')
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
            raise Exception(f"Asset with id {asset_id} not found")

        # mark the bot status as PROGRESS if the status is QUEUED
        if bot_data["status"] == "QUEUED":
            db.execute(
                f"UPDATE public.bot SET status = 'PROGRESS' WHERE id = {bot_id};")
            logger.info(f"Bot is in PROGRESS now")

        asset_data = asset_data.iloc[0]
        if asset_data["status"] != "PENDING":
            raise Exception(
                f"Asset with id {asset_id} is not PENDING. Skipping processing of asset {asset_id}")

        try:
            with db.connection:
                with db.connection.cursor() as cur:
                    logger.info("Processing asset")

                    if asset_data["type"] == "file":
                        # Download and save the file to the tmp folder.
                        file_path = download_file_from_url(
                            asset_data["value"], TMP_FOLDER_PATH, logger)

                        logger.info(
                            f"File with url {asset_data['value']} downloaded to {file_path}")

                        if file_path is None:
                            raise Exception(
                                f"Failed to download file from url: {asset_data['value']}")

                        # get the mime type of the file
                        # if file is pdf, use the pdf text extractor
                        # if file is doc/docx, use the doc text extractor
                        # raise exception for other file types
                        logger.info(f"File mime type: {mime_type}")
                        if mime_type == "application/pdf":
                            logger.debug(f"Processing pdf file {file_path}")
                            with open(file_path, 'rb') as file:
                                blob = Blob(data=file.read(), source=file_path)
                            parser = PDFPlumberParser(extract_images=False)
                            documents = parser.lazy_parse(blob)
                        elif mime_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                            logger.debug(f"Processing doc file {file_path}")
                            loader = Docx2txtLoader(file_path)
                            documents = loader.lazy_load()
                        else:
                            raise Exception(
                                f"Invalid mimetype {mime_type} for file {file_path}")
                    else:
                        # use proxy to get html from the url
                        html = scrape_url_smartproxy(
                            asset_data["value"], logger)
                        if html is None:
                            raise Exception(
                                f"Failed to get html from url: {asset_data['value']}")
                        # create documents from the html with the necessary metadata
                        soup = BeautifulSoup(html, 'html.parser')
                        # extract title, meta description, meta keywords
                        description = soup.find(
                            'meta', attrs={'name': 'description'})
                        keywords = soup.find(
                            'meta', attrs={'name': 'keywords'})
                        metadata = {
                            'title': soup.title.string if soup.title else '',
                            'description': description['content'] if description else '',
                            'keywords': keywords['content'] if keywords else ''
                        }

                        # find page content in body (exclude img, script, style, svg, iframe, video, audio, object, embed, canvas)
                        excluded_tags = ['img', 'script', 'style', 'svg',
                                         'iframe', 'video', 'audio', 'object', 'embed', 'canvas']
                        for tag in excluded_tags:
                            for el in soup.find_all(tag):
                                el.extract()

                        main_content_containers = [
                            'main', 'body'
                        ]
                        main = None
                        for selector in main_content_containers:
                            main = soup.select_one(selector)
                            if main:
                                break

                        if main:
                            content = main.get_text()
                        else:
                            content = soup.get_text()

                        content = re.sub(r'\n{2,}', '\n', content)
                        content = re.sub(r'\t{2,}', ' ', content)
                        content = re.sub(r' +', ' ', content)

                        documents = [
                            Document(page_content=content, metadata=metadata)]

                    # use the documents to chunk the text
                    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                        model_name=OPENAI_MODEL,
                        chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS)

                    chunks = splitter.split_documents(documents)

                    # create embeddings for the chunks and save them to the db
                    openai_client = OpenAI(api_key=OPENAI_API_KEY)
                    embeddings = openai_client.embeddings.create(input=[
                        chunk.page_content.replace("\n", " ") for chunk in chunks
                    ], model=OPENAI_EMBEDDING_MODEL, dimensions=OPENAI_EMBEDDINGS_DIMS).data

                    for i, chunk in enumerate(chunks):
                        page_content = chunk.page_content.replace("'", "''")
                        # remove non-printable characters
                        page_content = ''.join(
                            filter(lambda x: x in string.printable, page_content))

                        if chunk.metadata is not None:
                            for k, v in chunk.metadata.items():
                                if isinstance(k, str):
                                    k = k.replace("'", "''")
                                if isinstance(v, str):
                                    v = v.replace("'", "''")
                                chunk.metadata[k] = v

                        query = f"""
                        INSERT INTO public.embedding (embedding, chunk_text, chunk_metadata, asset_id)
                        VALUES ('{embeddings[i].embedding}', '{page_content}', '{json.dumps(chunk.metadata) if chunk.metadata else {}}', {asset_id});
                        """
                        cur.execute(query)

                    logger.info(
                        f"Asset processed successfully. Marking the asset as SUCCESS")
                    cur.execute(
                        f"UPDATE public.asset SET status = 'SUCCESS' WHERE id = {asset_id};")

        except Exception as e:
            capture_exception(
                e, metadata={"asset_id": asset_id, "bot_id": bot_id})
            traceback.print_exc()
            logger.error("Marking the asset as FAILED")
            db.execute(
                f"UPDATE public.asset SET status = 'FAILED' WHERE id = {asset_id};")

        def isnumber(x):
            try:
                return math.isfinite(x)
            except:
                return False

        try:
            ########## Update the bot status ##########
            # if the current asset has a parent_asset_id, get the status of all assets with the same parent_asset_id
            if isnumber(asset_data["parent_asset_id"]):
                logger.info(f"Asset is a child of sitemap")
                # currently this means the asset belongs to a sitemap (practice url)
                # get all the assets with the same parent_asset_id
                assets_with_same_parent = db.query(f"""
                                        SELECT a.id, a.status
                                        FROM public.asset a
                                        WHERE a.parent_asset_id = {asset_data["parent_asset_id"]}
                                        AND a.deleted_at IS NULL;""")

                if assets_with_same_parent[assets_with_same_parent["status"] == "PENDING"].empty:
                    # if all the assets have been processed once (status is not PENDING):
                    #     - if at least 25% of the assets are SUCCESS, mark the parent_asset_id as SUCCESS
                    #     - else, mark the asset corresponding to the parent_asset_id as FAILED
                    logger.info(
                        f"All assets with parent_asset_id {asset_data['parent_asset_id']} have been processed at least once")
                    successful_assets = assets_with_same_parent[assets_with_same_parent["status"] == "SUCCESS"]
                    if successful_assets.shape[0] >= PRACTICE_URL_SUCCESS_RATE * assets_with_same_parent.shape[0]:
                        logger.info(
                            f"At least {PRACTICE_URL_SUCCESS_RATE * 100}% of the assets with parent_asset_id {asset_data['parent_asset_id']} are SUCCESS. Marking the parent asset as SUCCESS")
                        db.execute(
                            f"UPDATE public.asset SET status = 'SUCCESS' WHERE id = {asset_data['parent_asset_id']};")
                    else:
                        logger.info(
                            f"Less than {PRACTICE_URL_SUCCESS_RATE * 100}% of the assets with parent_asset_id {asset_data['parent_asset_id']} are SUCCESS. Marking the parent asset as FAILED")
                        db.execute(
                            f"UPDATE public.asset SET status = 'FAILED' WHERE id = {asset_data['parent_asset_id']};")

            # get all the top level assets for the bot along with their statuses
            top_level_bot_assets = db.query(f"""
                                        SELECT a.id, a.status, a.type, a.value
                                        FROM public.asset a
                                        WHERE a.id IN (
                                            SELECT ba.asset_id
                                            FROM public.bot_assets ba
                                            WHERE ba.bot_id = {bot_id} AND ba.deleted_at IS NULL
                                        ) AND a.parent_asset_id IS NULL;
                                        """)

            # if all top level assets (with no parent_asset_id) are completed, mark the bot as completed in the db
            if top_level_bot_assets[top_level_bot_assets["status"] == "SUCCESS"].shape[0] == top_level_bot_assets.shape[0]:
                logger.info(
                    f"All top level assets for bot with id {bot_id} are completed. Marking the bot as SUCCESS")
                db.execute(
                    f"UPDATE public.bot SET status = 'SUCCESS' WHERE id = {bot_id};")

            # if any top level asset is failed, mark the bot as failed in the db
            if not top_level_bot_assets[top_level_bot_assets["status"] == "FAILED"].empty:
                logger.info(
                    f"Bot with id {bot_id} has some failed top level assets. Marking the bot as FAILED")
                db.execute(
                    f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")
        except Exception as e:
            capture_exception(
                e, metadata={"bot_id": bot_id, "asset_id": asset_id})
            traceback.print_exc()
            logger.error(
                "Failed to update the bot status. Marking the bot as FAILED")
            db.execute(
                f"UPDATE public.bot SET status = 'FAILED' WHERE id = {bot_id};")

    except Exception as e:
        capture_exception(e, metadata={"bot_id": bot_id, "asset_id": asset_id})
        traceback.print_exc()
    finally:
        message.ack()


def heartbeat():
    while True:
        connection.heartbeat.send_heartbeat_impl()
        time.sleep(10)


def cleartemp():
    # delete files older than 30min in the tmp folder
    while True:
        try:
            g = glob.glob(f"{TMP_FOLDER_PATH}/*")
            for f in g:
                last_mod_time = os.path.getmtime(f)

                if (datetime.datetime.now() - datetime.datetime.fromtimestamp(last_mod_time)).total_seconds() > 1800:
                    logger.debug(f"Deleting file {f}")
                    os.remove(f)
        except Exception:
            traceback.print_exc()

        time.sleep(120)


def main():
    try:
        logger.info("Starting asset processor")
        channel.basic.qos(prefetch_count=1)
        channel.basic.consume(
            handle_message, queue=INPUT_QUEUE_NAME, no_ack=False)

        logger.info(f'waiting for messages on {INPUT_QUEUE_NAME}')

        # start a daemon thread to call connection.process_data_events() every 10s
        # to prevent the connection from closing
        threading.Thread(target=heartbeat, daemon=True).start()
        threading.Thread(target=cleartemp, daemon=True).start()

        channel.start_consuming()
    except Exception as e:
        capture_exception(e)
        traceback.print_exc()
    finally:
        channel.close()
        connection.close()
