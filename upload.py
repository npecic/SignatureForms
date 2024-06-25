import os
import shutil
import logging
from flask import Flask, request, jsonify, flash, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, ALLOWED_EXTENSIONS
from signature_detection import signature_detector
import aiofiles
import asyncio

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def save_file(file, upload_folder):
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(file.read())
    return filepath

async def process_file(filepath):
    try:
        reader = PdfReader(filepath)
        signature_pages = await signature_detector.detect_signature_pages(reader, filepath)
        num_signatures = len(signature_pages)

        if signature_pages:
            # Extract only the base name of the file without the folder path
            output_filename = f'{os.path.splitext(os.path.basename(filepath))[0]}_{num_signatures}_signatures.pdf'
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            await signature_detector.extract_signature_pages(reader, signature_pages, output_filepath)
            return (f'Processed {os.path.basename(filepath)}.'f'<br>Total number of signatures: <span class="signature-count">{num_signatures}</span>'), output_filename, num_signatures
        else:
            return f'Processed {os.path.basename(filepath)}:<br>No signature pages detected.', None, num_signatures
    except Exception as e:
        logging.error(f"Error processing PDF file {filepath}: {e}")
        return f'Error processing {os.path.basename(filepath)}.', None, 0

@app.route('/upload', methods=['GET', 'POST'])
async def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')

    if 'files' not in request.files:
        flash('No files part')
        return jsonify({'status': 'error', 'message': 'No files part'}), 400

    files = request.files.getlist('files')
    if not files or not all(allowed_file(file.filename) for file in files):
        flash('No allowed files selected')
        return jsonify({'status': 'error', 'message': 'No allowed files selected'}), 400

    # Asynchronously save files
    filepaths = await asyncio.gather(*[save_file(file, UPLOAD_FOLDER) for file in files])

    # Asynchronously process files
    results = await asyncio.gather(*[process_file(filepath) for filepath in filepaths])

    # Clean up the upload folder after processing
    await cleanup_upload_folder(UPLOAD_FOLDER)

    messages = [result[0] for result in results]
    download_links = [result[1] for result in results]
    signatures_count = [result[2] for result in results]

    flash('\n'.join(messages))
    return jsonify({'status': 'success', 'messages': messages, 'download_links': download_links, 'signatures_count': signatures_count})

async def cleanup_upload_folder(folder):
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                logging.info(f"Deleted folder: {file_path}")
    except Exception as e:
        logging.error(f"Error cleaning up upload folder: {e}")

if __name__ == '__main__':
    app.run(debug=True)
