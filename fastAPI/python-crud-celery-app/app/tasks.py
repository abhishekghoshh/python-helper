from celery import Celery
from pymongo import MongoClient
import os

# Initialize Celery
celery = Celery('tasks', broker=os.getenv('RABBITMQ_URL'))

# MongoDB client
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['user_database']
users_collection = db['users']

@celery.task
def add_user(user_data):
    """Task to add a user to the MongoDB database."""
    result = users_collection.insert_one(user_data)
    return str(result.inserted_id)