from logging import Logger
import time
import urllib.parse

from usp.tree import sitemap_tree_for_homepage
from bs4 import BeautifulSoup
import requests

from envs import SMARTPROXY_AUTH


def get_sitemap_url(practice_url: str, logger: Logger):
    parsed_url = urllib.parse.urlparse(practice_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    common_sitemap_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap/sitemap.xml",
        "/sitemap/sitemap_index.xml",
        "/sitemap/sitemap.xml.gz",
        "/sitemap/sitemap_index.xml.gz",
    ]

    for path in common_sitemap_paths:
        url = f"{base_url}{path}"
        try:
            response = requests.get(url)
            if response.ok and 'text/xml' in response.headers.get('content-type', '').lower():
                return url
        except:
            pass

    logger.info(
        "No sitemap found in the common paths. Trying to find sitemap url from the home page.")
    try:
        html = scrape_url_smartproxy(practice_url, logger)
        if html is None:
            return None

        # find the sitemap url from the home page
        soup = BeautifulSoup(html, 'html.parser')
        link_tags = soup.find_all('link')
        for tag in link_tags:
            if tag.get('rel') == 'sitemap':
                return tag.get('href')
    except:
        return None


def scrape_sitemap(sitemap_url: str):
    s = sitemap_tree_for_homepage(sitemap_url)

    urls = [p.url for p in s.all_pages()]

    return list(set(urls))


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
