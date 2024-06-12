import shutil
import tempfile
from datetime import datetime

from PyPDF2 import PdfFileReader, PdfReader
from flask import Flask, redirect, url_for, render_template, send_from_directory, request, send_file, jsonify

import utils
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, SECRET_KEY, MISMATCH_FOLDER
from notifications import get_notifications, get_all_notifications, get_all_files
from pdf_compare import compare_pdf_folders
from upload import upload_file
from signature_detection import signature_detector
import zipfile
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MISMATCH_DIR'] = MISMATCH_FOLDER
app.secret_key = SECRET_KEY  # Required for flashing messages


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/compare')
def compare():
    return render_template('compare.html')


@app.route('/compare_pdfs', methods=['POST'])
def compare_pdfs_route():
    data = request.json
    folder1 = data.get('folder1')
    folder2 = data.get('folder2')

    if not folder1 or not folder2:
        return jsonify({"error": "Both folder paths are required"}), 400

    mismatch_dir = 'misMatch'
    mismatches = compare_pdf_folders(folder1, folder2, mismatch_dir)

    return jsonify({"mismatch_pdfs": mismatches})

@app.route('/clear_mismatched_folder', methods=['POST'])
def clear_mismatched_folder():
    try:
        # Remove all files in the upload directory
        for filename in os.listdir(MISMATCH_FOLDER):
            file_path = os.path.join(MISMATCH_FOLDER, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/mismatched_files/<filename>')
def download_mismatch_file(filename):
    return send_from_directory(app.config['MISMATCH_DIR'], filename, as_attachment=True, mimetype='application/pdf')

@app.route('/download_all_mismatched')
def download_all_mismatched():
    # Get all files in the mismatched folder
    mismatched_files = os.listdir(app.config['MISMATCH_DIR'])

    # Create a timestamp for the zip file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Define the zip filename
    zip_filename = f'mismatched_files_{timestamp}.zip'

    # Create a temporary directory to store the files to be zipped
    temp_dir = tempfile.mkdtemp()

    # Copy all mismatched files to the temporary directory
    for filename in mismatched_files:
        shutil.copy(os.path.join(app.config['MISMATCH_DIR'], filename), temp_dir)

    # Create the zip file
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in os.listdir(temp_dir):
            zipf.write(os.path.join(temp_dir, file), file)

    # Remove the temporary directory
    shutil.rmtree(temp_dir)

    # Send the zip file as an attachment
    return send_file(zip_filename, as_attachment=True)

@app.route('/get_keywords')
def get_keywords():
    primary_keywords = [pattern.pattern for pattern in signature_detector.primary_keyword_patterns]
    secondary_keywords = [pattern.pattern for pattern in signature_detector.secondary_keyword_patterns]
    return jsonify({
        'primary_keywords': primary_keywords,
        'secondary_keywords': secondary_keywords
    })


@app.route('/notifications')
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications, total_pages = get_notifications(page=page, output_folder=app.config['OUTPUT_FOLDER'])
    return render_template('notifications.html', notifications=notifications, page=page, total_pages=total_pages)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    return upload_file()


@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/clear_upload_dir', methods=['POST'])
def clear_upload_dir():
    try:
        # Remove all files in the upload directory
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_output_directory', methods=['POST'])
def clear_output_directory():
    try:
        # Remove all files in the output directory
        for filename in os.listdir(OUTPUT_FOLDER):
            file_path = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/download-all')
def download_all():
    from notifications import get_all_files  # Import inside the function to avoid circular import
    all_files = get_all_files(app.config['OUTPUT_FOLDER'])

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Current timestamp

    zip_filename = f'all_files_{timestamp}.zip'  # Include timestamp in the filename

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in all_files:
            zipf.write(file, os.path.basename(file))

    return send_file(zip_filename, as_attachment=True)


@app.route('/set_keywords', methods=['POST'])
def set_keywords():
    data = request.json
    keyword_option = data.get('keyword_option')

    if keyword_option == 'default':
        signature_detector.load_default_keywords()
    else:
        primary_keywords = ';'.join(data.get('primary_keywords', []))
        secondary_keywords = ';'.join(data.get('secondary_keywords', []))

        # If secondary_keywords is an empty string, set it to an empty list
        if secondary_keywords == "":
            secondary_keywords_list = []
        else:
            secondary_keywords_list = secondary_keywords.split(';')

        primary_keywords_list = primary_keywords.split(';')

        signature_detector.set_keywords(primary_keywords_list, secondary_keywords_list)
        signature_detector.save_keywords_to_json('data/manualKeywords.json', primary_keywords_list, secondary_keywords_list)

    return jsonify({'message': 'Keywords updated successfully'})



@app.route('/detect_signature_pages', methods=['POST'])
async def detect_signature_pages():
    data = await request.json
    pdf_path = data['pdf_path']
    pdf_reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(pdf_reader, pdf_path)
    return jsonify({'pages': pages})

@app.route('/extract_signature_pages', methods=['POST'])
async def extract_signature_pages():
    data = await request.json
    pdf_path = data['pdf_path']
    output_path = data['output_path']
    reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(reader, pdf_path)
    await signature_detector.extract_signature_pages(reader, pages, output_path)
    return jsonify(
        {'status': 'success', 'message': 'Signature pages extracted successfully', 'output_path': output_path})

@app.route('/export-file-names')
def export_file_names():
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
def report():
    notifications = get_all_notifications(output_folder=app.config['OUTPUT_FOLDER'])
    return render_template('report.html', notifications=notifications)




if __name__ == '__main__':
    app.run(debug=True)