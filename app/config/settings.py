import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mydatabase')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'