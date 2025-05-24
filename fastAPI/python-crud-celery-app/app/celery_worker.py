from celery import Celery
import os

# Initialize the Celery application
celery_app = Celery('tasks', broker=os.environ.get('RABBITMQ_URL'))

@celery_app.task
def add_user_to_db(user_data):
    from app.models import User
    from app.utils import save_user_to_db

    # Process the user data and save it to the database
    user = User(**user_data)
    save_user_to_db(user)