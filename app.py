import logging
import shutil
import tempfile
import threading
import time
from datetime import datetime
import zipfile
import os
from flask import Flask, redirect, url_for, render_template, send_from_directory, request, send_file, jsonify, after_this_request, session
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit

import utils
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, SECRET_KEY, MISMATCH_FOLDER, MATCH_FOLDER, BASELINE_IMG_FOLDER, CHANGED_IMG_FOLDER, MAX_CONTENT_LENGTH
from notifications import get_notifications, get_all_notifications
from pdf_compare import compare_pdf_folders
from upload import upload_file, process_file
from signature_detection import signature_detector

app = Flask(__name__)
app.secret_key = SECRET_KEY
socketio = SocketIO(app)

# Load configuration from config.py
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MISMATCH_DIR'] = MISMATCH_FOLDER
app.config['MATCH_DIR'] = MATCH_FOLDER
app.config['BASELINE_IMG'] = BASELINE_IMG_FOLDER
app.config['CHANGED_IMG'] = CHANGED_IMG_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define the root directory for temporary files
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(ROOT_DIR, 'temp')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

async def update_progress(progress, message):
    socketio.emit('progress_update', {'progress': progress, 'message': message})

@app.route('/')
async def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
async def dashboard():
    return render_template('dashboard.html')

@app.route('/compare')
async def compare():
    return render_template('compare.html')


@app.route('/upload_file_chunk', methods=['POST'])
def upload_file_chunk():
    chunk = request.files['chunk']
    file_name = request.form['fileName']
    chunk_number = int(request.form['chunkNumber'])
    total_chunks = int(request.form['totalChunks'])
    upload_folder = app.config['UPLOAD_FOLDER']

    # Determine which temp directory to use based on conditions
    if 'temp_dir1' not in session:
        session['temp_dir1'] = tempfile.mkdtemp(dir=upload_folder)
    temp_dir = session['temp_dir1']

    # Create the temporary directory if it doesn't exist
    os.makedirs(temp_dir, exist_ok=True)

    chunk_save_path = os.path.join(temp_dir, f"{file_name}_chunk_{chunk_number}")
    chunk.save(chunk_save_path)

    if chunk_number == total_chunks - 1:
        final_file_path = os.path.join(upload_folder, file_name)
        with open(final_file_path, 'wb') as final_file:
            for i in range(total_chunks):
                chunk_file_path = os.path.join(temp_dir, f"{file_name}_chunk_{i}")
                with open(chunk_file_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
                os.remove(chunk_file_path)

        # Cleanup the temporary directory
        shutil.rmtree(temp_dir)

        # Emit progress update
        progress = 100
        message = 'File upload complete'
        socketio.emit('progress_update', {'progress': progress, 'message': message})

        return jsonify({'status': 'success', 'message': 'File upload complete', 'filePath': final_file_path})

    # Calculate progress
    progress = (chunk_number + 1) / total_chunks * 100
    message = f'Chunk {chunk_number + 1} of {total_chunks} uploaded'
    socketio.emit('progress_update', {'progress': progress, 'message': message})

    return jsonify({'status': 'success', 'message': 'Chunk uploaded successfully'})

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

@app.route('/process_file', methods=['POST'])
async def process_file_endpoint():
    data = request.get_json()
    file_path = data.get('filePath')
    if not file_path or not os.path.isfile(file_path):
        return jsonify({'status': 'error', 'message': 'Invalid file path'}), 400

    result = await process_file(file_path)
    return jsonify({'status': 'success', 'message': result[0], 'downloadLink': result[1], 'signaturesCount': result[2]})


@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk = request.files['chunk']
    file_name = request.form['fileName']
    chunk_number = int(request.form['chunkNumber'])
    total_chunks = int(request.form['totalChunks'])
    folder = request.form['folder']

    if folder == 'folder1':
        if 'temp_dir1' not in session:
            session['temp_dir1'] = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
        temp_dir = session['temp_dir1']
    else:
        if 'temp_dir2' not in session:
            session['temp_dir2'] = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
        temp_dir = session['temp_dir2']

    os.makedirs(temp_dir, exist_ok=True)

    chunk_save_path = os.path.join(temp_dir, f"{file_name}_chunk_{chunk_number}")
    chunk.save(chunk_save_path)

    if chunk_number == total_chunks - 1:
        with open(os.path.join(temp_dir, file_name), 'wb') as final_file:
            for i in range(total_chunks):
                chunk_file_path = os.path.join(temp_dir, f"{file_name}_chunk_{i}")
                with open(chunk_file_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
                os.remove(chunk_file_path)

    return jsonify({'status': 'success'})

@app.route('/upload_folders', methods=['POST'])
async def upload_folders():
    try:
        folder1_files = request.files.getlist('folder1')
        folder2_files = request.files.getlist('folder2')

        if 'temp_dir1' not in session:
            session['temp_dir1'] = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
        if 'temp_dir2' not in session:
            session['temp_dir2'] = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])

        temp_dir1 = session['temp_dir1']
        temp_dir2 = session['temp_dir2']

        for file in folder1_files:
            filename = secure_filename(os.path.basename(file.filename))
            file.save(os.path.join(temp_dir1, filename))

        for file in folder2_files:
            filename = secure_filename(os.path.basename(file.filename))
            file.save(os.path.join(temp_dir2, filename))

        logging.debug(f'Files uploaded to temporary directories: {temp_dir1}, {temp_dir2}')
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f'Error in upload_folders: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/compare_pdfs', methods=['POST'])
async def compare_pdfs_route():
    try:
        temp_dir1 = session.get('temp_dir1')
        temp_dir2 = session.get('temp_dir2')

        if not temp_dir1 or not temp_dir2:
            return jsonify({'matches': [], 'mismatches': []})

        result = compare_pdf_folders(temp_dir1, temp_dir2, app.config['MISMATCH_DIR'], app.config['MATCH_DIR'])

        shutil.rmtree(temp_dir1)
        shutil.rmtree(temp_dir2)

        return jsonify({'matches': result["matches"], 'mismatches': result["mismatches"]})
    except Exception as e:
        logging.error(f'Error in compare_pdfs_route: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download_compare_file/<filetype>/<filename>')
def download_compare_file(filetype, filename):
    if filetype == 'match':
        directory = app.config['MATCH_DIR']
    elif filetype == 'mismatch':
        directory = app.config['MISMATCH_DIR']
    else:
        return jsonify({"status": "error", "message": "Invalid file type"}), 400

    return send_from_directory(directory, filename)

@app.route('/clear_mismatched_folder', methods=['POST'])
async def clear_mismatched_folder():
    try:
        mismatch_dir = app.config['MISMATCH_DIR']
        logging.debug(f'Trying to clear mismatched folder at: {mismatch_dir}')

        if not os.path.exists(mismatch_dir):
            logging.error(f'Mismatched directory does not exist: {mismatch_dir}')
            return jsonify({"status": "error", "message": "Mismatched directory does not exist"}), 500

        for filename in os.listdir(mismatch_dir):
            file_path = os.path.join(mismatch_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f'Error removing file {file_path}: {str(e)}')

        logging.debug(f'Mismatched folder cleared: {mismatch_dir}')
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f'Error in clear_mismatched_folder: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_matched_folder', methods=['POST'])
async def clear_matched_folder():
    try:
        match_dir = app.config['MATCH_DIR']
        logging.debug(f'Trying to clear matched folder at: {match_dir}')

        if not os.path.exists(match_dir):
            logging.error(f'Matched directory does not exist: {match_dir}')
            return jsonify({"status": "error", "message": "Matched directory does not exist"}), 500

        for filename in os.listdir(match_dir):
            file_path = os.path.join(match_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f'Error removing file {file_path}: {str(e)}')

        logging.debug(f'Matched folder cleared: {match_dir}')
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f'Error in clear_matched_folder: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_compare_img', methods=['POST'])
async def clear_compare_img_folder():
    folders_to_clear = [app.config['BASELINE_IMG'], app.config['CHANGED_IMG']]
    try:
        for folder in folders_to_clear:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) or os.link(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def delayed_cleanup(path, delay=10):
    def cleanup():
        time.sleep(delay)
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
        except Exception as e:
            app.logger.error(f'Error during delayed cleanup: {e}')

    thread = threading.Thread(target=cleanup)
    thread.start()

@app.route('/download/<download_type>')
def download_files(download_type):
    try:
        if (download_type == 'matched'):
            directory = app.config['MATCH_DIR']
            zip_prefix = 'matched_files'
        elif (download_type == 'mismatched'):
            directory = app.config['MISMATCH_DIR']
            zip_prefix = 'mismatched_files'
        elif (download_type == 'all'):
            directory = app.config['OUTPUT_FOLDER']
            zip_prefix = 'all_files'
        else:
            return jsonify({"status": "error", "message": "Invalid download type"}), 400

        files = os.listdir(directory)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        temp_dir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
        zip_filename = os.path.join(temp_dir, f'{zip_prefix}_{timestamp}.zip')

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for filename in files:
                file_path = os.path.join(directory, filename)
                zipf.write(file_path, os.path.basename(file_path))

        @after_this_request
        def remove_file(response):
            delayed_cleanup(temp_dir)
            return response

        return send_file(zip_filename, as_attachment=True)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_keywords')
async def get_keywords():
    primary_keywords = [pattern.pattern for pattern in signature_detector.primary_keyword_patterns]
    secondary_keywords = [pattern.pattern for pattern in signature_detector.secondary_keyword_patterns]
    return jsonify({
        'primary_keywords': primary_keywords,
        'secondary_keywords': secondary_keywords
    })

@app.route('/notifications')
async def notifications():
    page = request.args.get('page', 1, type=int)
    notifications, total_pages = await get_notifications(page=page, output_folder=app.config['OUTPUT_FOLDER'])
    return render_template('notifications.html', notifications=notifications, page=page, total_pages=total_pages)

@app.route('/upload', methods=['GET', 'POST'])
async def upload():
    return await upload_file()

@app.route('/manual_compare')
async def manual_compare():
    return render_template('manual_compare.html')

@app.route('/api/get_compare_images', methods=['GET'])
async def get_compare_images():
    try:
        original_dir = 'static/manual_compare_img/original'
        bounding_dir = 'static/manual_compare_img/bounding_screenshot'

        original_images = sorted(os.listdir(original_dir))
        bounding_images = sorted(os.listdir(bounding_dir))

        if len(original_images) != len(bounding_images):
            raise ValueError("The number of original images and bounding images do not match")

        images = []
        for original, bounding in zip(original_images, bounding_images):
            images.append({
                'original': os.path.join(original_dir, original),
                'bounding_box': os.path.join(bounding_dir, bounding)
            })

        return jsonify({'images': images})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
async def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/clear_upload_dir', methods=['POST'])
async def clear_upload_dir():
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path) or os.link(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_output_directory', methods=['POST'])
async def clear_output_directory():
    try:
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            if os.path.isfile(file_path) or os.link(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/set_keywords', methods=['POST'])
async def set_keywords():
    data = request.get_json()  # Synchronous call
    keyword_option = data.get('keyword_option')

    if keyword_option == 'default':
        signature_detector.load_default_keywords()
    else:
        primary_keywords = ';'.join(data.get('primary_keywords', []))
        secondary_keywords = ';'.join(data.get('secondary_keywords', []))
        primary_keywords_list = primary_keywords.split(';')
        secondary_keywords_list = secondary_keywords.split(';') if secondary_keywords else []

        await signature_detector.set_keywords(primary_keywords_list, secondary_keywords_list)
        await signature_detector.save_keywords_to_json('data/manualKeywords.json', primary_keywords_list,
                                                       secondary_keywords_list)

    return jsonify({'message': 'Keywords updated successfully'})

@app.route('/detect_signature_pages', methods=['POST'])
async def detect_signature_pages():
    data = await request.get_json()  # Synchronous call
    pdf_path = data['pdf_path']
    pdf_reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(pdf_reader, pdf_path)
    return jsonify({'pages': pages})

@app.route('/extract_signature_pages', methods=['POST'])
async def extract_signature_pages():
    data = await request.get_json()  # Synchronous call
    pdf_path = data['pdf_path']
    output_path = data['output_path']
    reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(reader, pdf_path)

    with tempfile.TemporaryDirectory() as temp_output_dir:
        temp_pdf_path = os.path.join(temp_output_dir, "extracted_signatures.pdf")

        try:
            await signature_detector.extract_signature_pages(reader, pages, temp_pdf_path)
            shutil.move(temp_pdf_path, output_path)

            return jsonify({'status': 'success', 'message': 'Signature pages extracted successfully', 'output_path': output_path})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/export-file-names')
async def export_file_names():
    output_folder = app.config['OUTPUT_FOLDER']
    all_files = utils.get_all_files(output_folder)
    processed_files = []

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        processed_time = os.path.getmtime(file_path)
        processed_files.append({
            "title": file_name,
            "timestamp": processed_time
        })

    pdf_buffer = utils.generate_pdf(processed_files, output_folder)
    return send_file(pdf_buffer, as_attachment=True, download_name='processed_files.pdf', mimetype='application/pdf')

@app.route('/report')
async def report():
    notifications = await get_all_notifications(output_folder=app.config['OUTPUT_FOLDER'])
    return render_template('report.html', notifications=notifications)

if __name__ == '__main__':
    socketio.run(app, debug=True)
