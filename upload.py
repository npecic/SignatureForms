import os
import logging
import shutil
import aiofiles
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, BATCH_SIZE
from signature_detection import signature_detector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH  # Set the maximum upload size
app.config['BATCH_SIZE'] = BATCH_SIZE  # Declare batch size

logging.basicConfig(level=logging.DEBUG)

# Using ProcessPoolExecutor for CPU-bound tasks
process_executor = ProcessPoolExecutor(max_workers=os.cpu_count()*2)
# Using ThreadPoolExecutor for I/O-bound tasks
io_executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 3)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def save_file(file, upload_folder, filename=None):
    if not filename:
        filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(file.read())
    logging.debug(f"Saved file {filename} to {filepath}")
    return filepath

def process_file_sync(filepath):
    return asyncio.run(process_file(filepath))

async def process_file(filepath):
    logging.debug(f"Processing file: {filepath}")
    try:
        reader = PdfReader(filepath)
        signature_pages = await signature_detector.detect_signature_pages(reader, filepath)
        num_signatures = len(signature_pages)

        if signature_pages:
            output_filename = f'{os.path.splitext(os.path.basename(filepath))[0]}_{num_signatures}_signatures.pdf'
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            await signature_detector.extract_signature_pages(reader, signature_pages, output_filepath)
            return f'Processed {os.path.basename(filepath)}.<br>Total number of signatures: <span class="signature-count">{num_signatures}</span>', output_filename, num_signatures
        else:
            return f'Processed {os.path.basename(filepath)}:<br>No signature pages detected.', None, num_signatures
    except Exception as e:
        logging.error(f"Error processing PDF file {filepath}: {e}")
        return f'Error processing {os.path.basename(filepath)}.', None, 0

async def cleanup_upload_folder():
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                logging.info(f"Deleted folder: {file_path}")
        logging.info("Upload folder cleaned up successfully.")
    except Exception as e:
        logging.error(f"Error cleaning up upload folder: {e}")

@app.route('/upload', methods=['GET', 'POST'])
async def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')

    if 'files' not in request.files:
        return jsonify({'status': 'error', 'message': 'No files part'}), 400

    files = request.files.getlist('files')
    if not files or not all(allowed_file(file.filename) for file in files):
        return jsonify({'status': 'error', 'message': 'No allowed files selected'}), 400

    batch_size = app.config['BATCH_SIZE']
    total_files = len(files)
    all_results = []

    for i in range(0, total_files, batch_size):
        batch_files = files[i:i + batch_size]
        filepaths = await asyncio.gather(*[save_file(file, UPLOAD_FOLDER) for file in batch_files])

        # Process the files concurrently using ProcessPoolExecutor
        loop = asyncio.get_event_loop()
        results = await asyncio.gather(*[loop.run_in_executor(process_executor, process_file_sync, filepath) for filepath in filepaths])
        all_results.extend(results)

    messages = [result[0] for result in all_results]
    download_links = [result[1] for result in all_results]
    signatures_count = [result[2] for result in all_results]

    # Clean up the upload folder after processing
    logging.info("Starting cleanup of upload folder.")
    await cleanup_upload_folder()

    return jsonify({'status': 'success', 'messages': messages, 'download_links': download_links, 'signatures_count': signatures_count})

@app.route('/clear_upload_dir', methods=['POST'])
async def clear_upload_dir():
    try:
        await cleanup_upload_folder()
        return jsonify({'status': 'success', 'message': 'Upload directory cleared successfully.'})
    except Exception as e:
        logging.error(f"Error clearing upload directory: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
