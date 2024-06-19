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
FOLDER1_DIR = os.getenv('FOLDER1_DIR', 'folder1')
FOLDER2_DIR = os.getenv('FOLDER2_DIR', 'folder2')


ALLOWED_EXTENSIONS = {'pdf'}
SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')