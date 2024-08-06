import redis

from settings import REDIS_URL
from utils.split_url import split_url


class Cache:
    def __init__(self):
        urlparts = split_url(REDIS_URL)
        kwargs = {
            'host': urlparts['host'],
            'port': urlparts['port'],
            'password': urlparts['password'],
            'username': urlparts['user'],
        }

        if urlparts['scheme'] == 'rediss':
            kwargs['connection_class'] = redis.SSLConnection

        self.pool = redis.connection.BlockingConnectionPool(**kwargs)
        self.redis = redis.StrictRedis(connection_pool=self.pool)

    def set(self, key, value, ttl=None):
        self.redis.set(key, value, ex=ttl)

    def delete(self, key):
        self.redis.delete(key)

    def get(self, key):
        val = self.redis.get(key)
        if val:
            return val.decode("utf-8")

        return None


cache = Cache()
