from flask import Flask
from celery import Celery

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        # Configuration settings can be added here
        MONGO_URI='mongodb://mongo:27017/mydatabase',
        CELERY_BROKER_URL='amqp://rabbitmq'
    )

    # Initialize Celery
    celery = make_celery(app)

    # Register blueprints or routes here
    from .api import api_bp
    app.register_blueprint(api_bp)

    return app

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    return celery

app = create_app()