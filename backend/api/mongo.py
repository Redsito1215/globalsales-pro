from pymongo import MongoClient
from config.settings import settings

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri)
    return _client[settings.mongo_db]

def col(name: str):
    return get_db()[name]
