from urllib.parse import urlparse


def split_url(url):
    parsed_url = urlparse(url)

    scheme = parsed_url.scheme
    host = parsed_url.hostname
    port = parsed_url.port
    user = parsed_url.username
    password = parsed_url.password

    return {
        'scheme': scheme,
        'host': host,
        'port': port,
        'user': user,
        'password': password
    }
