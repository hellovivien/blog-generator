from tinydb import TinyDB # minimalist document oriented database 
from tinydb.storages import JSONStorage
from tinydb_serialization import SerializationMiddleware
from tinydb_serialization.serializers import DateTimeSerializer


class Database:
    def __init__(self):
        serialization = SerializationMiddleware(JSONStorage)
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        self.db = TinyDB('db.json', storage=serialization)

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()