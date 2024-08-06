import uuid
import traceback
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from utils.capture_exception import capture_exception
from utils.logger import logger
from aws.session import session
from settings import S3_BUCKET, AWS_ENDPOINT_URL, FLASK_ENV, CLOUDFRONT_URL

s3 = session.resource('s3', endpoint_url=AWS_ENDPOINT_URL)
bucket = s3.Bucket(S3_BUCKET)


def get_url_for_object(key: str) -> str:
    if FLASK_ENV == "development" or not CLOUDFRONT_URL:
        aws_endpoint = AWS_ENDPOINT_URL.replace("localstack", "localhost")
        aws_endpoint = aws_endpoint.rstrip("/")
        return f"{aws_endpoint}/{S3_BUCKET}/{key}"
    else:
        aws_endpoint = CLOUDFRONT_URL
        aws_endpoint = aws_endpoint.rstrip("/")
        return f"{aws_endpoint}/{key}"


def upload_file(file: FileStorage, *, object_name=None, public=True) -> str:
    """Upload a file to an S3 bucket

    :param file: File to upload (FileStorage handle)
    :param object_name: S3 object name. If not specified then uuid + file_name is used
    :param public: Whether the file should be public or not (ignored when CLOUDFRONT_URL is set)
    :return: URL of the uploaded file
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = secure_filename(file.filename)
        # prepend uuid to the filename to avoid conflicts
        object_name = f"{str(uuid.uuid4().hex)}_{object_name}"

    file.stream.seek(0)
    args = {
        'ContentType': file.mimetype,
    }

    if CLOUDFRONT_URL is None:
        args['ACL'] = 'public-read' if public else 'private'

    # Upload the file
    bucket.upload_fileobj(file, object_name, ExtraArgs=args)

    # return the url of the uploaded file
    return get_url_for_object(object_name)


def delete_files(*urls: str):
    keys = [url.split("/")[-1] for url in urls]

    if not keys:
        return True

    try:
        resp = bucket.delete_objects(Delete={
            'Objects': [{'Key': key} for key in keys],
        })

        if resp.get("Errors"):
            logger.error(
                f"Errors occurred while deleting keys: {resp['Errors']}")
            return False

        return True
    except Exception as e:
        traceback.print_exc()
        capture_exception(e, metadata={
            "keys": keys
        })
        return False
