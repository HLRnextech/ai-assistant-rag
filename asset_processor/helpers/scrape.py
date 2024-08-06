from logging import Logger
import time

import requests

from envs import SMARTPROXY_AUTH


def scrape_url_smartproxy(url: str, logger: Logger):
    payload = {
        "headless": "html",
        "target": "universal",
        "url": url
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {SMARTPROXY_AUTH}"
    }
    t1 = time.time()
    response = requests.post(
        "https://scraper-api.smartproxy.com/v2/scrape", json=payload, headers=headers)
    t2 = time.time()
    data = response.json()
    logger.info(f'url: {url}')
    logger.info(f'smartproxy api response time: {t2-t1} seconds')
    logger.info(f'smartproxy task_id: {data["results"][0]["task_id"]}')
    if response.ok:
        html = data['results'][0]['content']
        return html
