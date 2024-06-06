from flask import Flask, request, jsonify, send_from_directory, flash, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from pytesseract import image_to_string
from pdf2image import convert_from_path
from datetime import datetime
import os
import re
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'outputs')
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')  # Required for flashing messages

# Ensure the upload and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Mock functions to simulate notification retrieval
def get_notifications():
    processed_files = []
    for filename in os.listdir(OUTPUT_FOLDER):
        if filename.endswith('.pdf'):
            num_signatures = filename.split('_')[0]  # Extract number of signatures from filename
            num_signatures = num_signatures.split('signatures')[0]  # Remove '_signatures' from the count
            processed_files.append({
                "title": "File Processed",
                "message": f"{filename}. {num_signatures} signature(s) is/are ready for download.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Use current timestamp
                "download_link": filename
            })
    return processed_files


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_signature_pages(pdf_reader, pdf_path):
    signature_pages = []
    primary_keywords = [
        'Attorney-in-fact', 'President and CEO', 'Authorized Company Representative', 'Senior Vice President',
        'John J. Willis', 'License Number: W327297', 'Signature', 'Director, Member Services'
    ]
    secondary_keywords = ['Signature Of Applicant/First Named Insured', "Applicant's/Named Insured's Signature", "Signature Of Applicant/Named Insured",
                          'Signature of Insured', 'Signature of Third Party Designee', 'Applicant Signature', 'Signature of Named Insured']

    primary_keyword_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) for keyword in primary_keywords]

    for page_num in range(len(pdf_reader.pages)):
        try:
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text:
                text = text.strip()
                primary_keyword_matched = any(pattern.search(text) for pattern in primary_keyword_patterns)
                if primary_keyword_matched:
                    secondary_keyword_matched = any(secondary_keyword.lower() in text.lower() for secondary_keyword in secondary_keywords)
                    if not secondary_keyword_matched:
                        signature_pages.append(page_num)
            else:
                images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
                for image in images:
                    ocr_text = image_to_string(image).strip()
                    primary_keyword_matched = any(pattern.search(ocr_text) for pattern in primary_keyword_patterns)
                    if primary_keyword_matched:
                        secondary_keyword_matched = any(secondary_keyword.lower() in ocr_text.lower() for secondary_keyword in secondary_keywords)
                        if not secondary_keyword_matched:
                            signature_pages.append(page_num)
        except Exception as e:
            logging.error(f"Error processing page {page_num} in PDF: {e}")

    return signature_pages


def extract_signature_pages(reader, page_nums, output_filepath):
    writer = PdfWriter()
    for page_num in page_nums:
        writer.add_page(reader.pages[page_num])
    with open(output_filepath, 'wb') as output_pdf:
        writer.write(output_pdf)


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/notifications')
def notifications():
    notifications = get_notifications()
    return render_template('notifications.html', notifications=notifications)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')

    if 'files' not in request.files:
        flash('No files part')
        return jsonify({'status': 'error', 'message': 'No files part'}), 400
    files = request.files.getlist('files')
    if not files or not all(allowed_file(file.filename) for file in files):
        flash('No allowed files selected')
        return jsonify({'status': 'error', 'message': 'No allowed files selected'}), 400

    messages = []
    download_links = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                reader = PdfReader(filepath)
                signature_pages = detect_signature_pages(reader, filepath)
                if signature_pages:
                    output_filename = f'{os.path.splitext(filename)[0]}_signatures.pdf'
                    output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                    extract_signature_pages(reader, signature_pages, output_filepath)
                    download_links.append(output_filename)
                    messages.append(
                        f'Processed {filename}: Extracted signature pages to {output_filename}. {len(signature_pages)} signatures' if len(signature_pages) > 1 else f'Processed {filename}: Extracted signature page to {output_filename}. 1 signature')
                else:
                    messages.append(f'Processed {filename}: No signature pages detected.')
                    download_links.append(None)  # Add None for files with no signature pages
            except Exception as e:
                logging.error(f"Error processing PDF file {filename}: {e}")
                messages.append(f'Error processing {filename}.')
                download_links.append(None)  # Add None for files with errors

    flash('\n'.join(messages))
    return jsonify({'status': 'success', 'messages': messages, 'download_links': download_links})


@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)