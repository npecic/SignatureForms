import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
ALLOWED_EXTENSIONS = {'pdf'}
SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')