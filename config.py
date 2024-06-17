import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
MISMATCH_FOLDER = os.getenv('MISMATCH_DIR', 'misMatch')
MATCH_FOLDER = os.getenv('MATCH_DIR', 'match')
BASELINE_IMG_FOLDER = os.getenv('BASELINE_IMG_FOLDER', 'static/manual_compare_img/original')
CHANGED_IMG_FOLDER = os.getenv('CHANGED_IMG_FOLDER', 'static/manual_compare_img/bounding_screenshot')

ALLOWED_EXTENSIONS = {'pdf'}
SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')