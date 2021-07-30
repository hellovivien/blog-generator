import os
from faker import Faker
fake = Faker('fr-FR')
from tinydb import TinyDB # minimalist document oriented database 
from passlib.hash import bcrypt
from datetime import datetime
from tinydb.storages import JSONStorage
from tinydb_serialization import SerializationMiddleware
from tinydb_serialization.serializers import DateTimeSerializer
from db import Database
import const
from datetime import timedelta
import random


def create_db():
    if os.path.exists(const.DB_PATH):
        os.remove(const.DB_PATH)
    else:
        open(const.DB_PATH, "x")
    users = []

if __name__ == '__main__':
    create_db()