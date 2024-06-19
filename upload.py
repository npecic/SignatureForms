import os
import logging
from flask import Flask, request, jsonify, flash, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, ALLOWED_EXTENSIONS
from signature_detection import signature_detector
import asyncio

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    messages = []
    download_links = []
    signatures_count = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)  # Save file synchronously

            try:
                reader = PdfReader(filepath)
                signature_pages = await signature_detector.detect_signature_pages(reader, filepath)
                num_signatures = len(signature_pages)
                signatures_count.append(num_signatures)

                if signature_pages:
                    output_filename = f'{os.path.splitext(filename)[0]}_{num_signatures}_signatures.pdf'
                    output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
                    await signature_detector.extract_signature_pages(reader, signature_pages, output_filepath)
                    download_links.append(output_filename)
                    messages.append(
                        f'Processed {filename}. Total number of signatures: <span class="signature-count">{num_signatures}</span> '
                    )
                else:
                    messages.append(f'Processed {filename}: No signature pages detected.')
                    download_links.append(None)  # Add None for files with no signature pages
            except Exception as e:
                logging.error(f"Error processing PDF file {filename}: {e}")
                messages.append(f'Error processing {filename}.')
                download_links.append(None)  # Add None for files with errors

    flash('\n'.join(messages))
    return jsonify({'status': 'success', 'messages': messages, 'download_links': download_links, 'signatures_count': signatures_count})

if __name__ == '__main__':
    app.run(debug=True)
