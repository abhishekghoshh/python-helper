from mongoengine import Document, StringField, EmailField

class User(Document):
    username = StringField(required=True, unique=True)
    email = EmailField(required=True, unique=True)
    full_name = StringField()
    password = StringField(required=True)