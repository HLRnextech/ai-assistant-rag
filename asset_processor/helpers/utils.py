from logging import Logger
import traceback
import os
import wget
from urllib.parse import urlparse
from pathlib import Path

from envs import ENV


def remove_file(file_path):
    if file_path is not None and os.path.exists(file_path):
        os.remove(file_path)


def get_file_name_from_url(url, default_ext=""):
    filename = os.path.basename(urlparse(url).path)
    ext = Path(filename).suffix
    if ext.strip() == "":
        filename += default_ext

    return filename


# TODO: use boto3 to download file from s3 url
def download_file_from_url(url: str, folder_path: str, logger: Logger):
    file_path = None
    try:
        filename = get_file_name_from_url(url, default_ext=".pdf")
        file_path = os.path.join(folder_path, filename)
        if ENV == "development":
            url = url.replace("localhost", "localstack")

        wget.download(url, file_path, bar=None)
        logger.info(f"File downloaded at {file_path}")
        return file_path
    except Exception:
        traceback.print_exc()
        remove_file(file_path)
        return
