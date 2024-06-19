import shutil
import tempfile
from datetime import datetime
import zipfile
import os
from flask import Flask, redirect, url_for, render_template, send_from_directory, request, send_file, jsonify, after_this_request
from PyPDF2 import PdfFileReader, PdfReader
import utils
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, SECRET_KEY, MISMATCH_FOLDER, MATCH_FOLDER, BASELINE_IMG_FOLDER, CHANGED_IMG_FOLDER
from notifications import get_notifications, get_all_notifications, get_all_files
from pdf_compare import compare_pdf_folders
from upload import upload_file
from signature_detection import signature_detector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MISMATCH_DIR'] = MISMATCH_FOLDER
app.config['MATCH_DIR'] = MATCH_FOLDER
app.config['BASELINE_IMG'] = BASELINE_IMG_FOLDER
app.config['CHANGED_IMG'] = CHANGED_IMG_FOLDER
app.secret_key = SECRET_KEY

@app.route('/')
async def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
async def dashboard():
    return render_template('dashboard.html')

@app.route('/compare')
async def compare():
    return render_template('compare.html')



@app.route('/compare_pdfs', methods=['POST'])
def compare_pdfs_route():
    data = request.json
    folder1 = data.get('folder1')
    folder2 = data.get('folder2')

    if not folder1 or not folder2:
        return jsonify({"error": "Both folder paths are required"}), 400

    # Ensure paths are absolute
    if not os.path.isabs(folder1):
        folder1 = os.path.abspath(folder1)
    if not os.path.isabs(folder2):
        folder2 = os.path.abspath(folder2)

    if not os.path.exists(folder1):
        return jsonify({"error": f"Folder1 path does not exist: {folder1}"}), 400
    if not os.path.exists(folder2):
        return jsonify({"error": f"Folder2 path does not exist: {folder2}"}), 400

    mismatches = compare_pdf_folders(folder1, folder2, app.config['MISMATCH_DIR'], app.config['MATCH_DIR'])

    return jsonify({"mismatch_pdfs": mismatches})

@app.route('/clear_mismatched_folder', methods=['POST'])
async def clear_mismatched_folder():
    try:
        for filename in os.listdir(app.config['MISMATCH_DIR']):
            file_path = os.path.join(app.config['MISMATCH_DIR'], filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_matched_folder', methods=['POST'])
async def clear_matched_folder():
    try:
        for filename in os.listdir(app.config['MATCH_DIR']):
            file_path = os.path.join(app.config['MATCH_DIR'], filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_compare_img', methods=['POST'])
async def clear_compare_img_folder():
    folders_to_clear = [app.config['BASELINE_IMG'], app.config['CHANGED_IMG']]
    try:
        for folder in folders_to_clear:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/<download_type>')
def download_files(download_type):
    try:
        if download_type == 'matched':
            directory = app.config['MATCH_DIR']
            zip_prefix = 'matched_files'
        elif download_type == 'mismatched':
            directory = app.config['MISMATCH_DIR']
            zip_prefix = 'mismatched_files'
        elif download_type == 'all':
            directory = app.config['OUTPUT_FOLDER']
            zip_prefix = 'all_files'
        else:
            return jsonify({"status": "error", "message": "Invalid download type"}), 400

        files = os.listdir(directory)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        temp_dir = tempfile.mkdtemp()
        zip_filename = os.path.join(temp_dir, f'{zip_prefix}_{timestamp}.zip')

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for filename in files:
                file_path = os.path.join(directory, filename)
                zipf.write(file_path, os.path.basename(file_path))

        @after_this_request
        def remove_file(response):
            try:
                os.remove(zip_filename)
                shutil.rmtree(temp_dir)
            except Exception as e:
                app.logger.error(f'Error removing or closing downloaded file handle: {e}')
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
            if os.path.isfile(file_path) or os.path.islink(file_path):
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
            if os.path.isfile(file_path) or os.path.islink(file_path):
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
        await signature_detector.save_keywords_to_json('data/manualKeywords.json', primary_keywords_list, secondary_keywords_list)

    return jsonify({'message': 'Keywords updated successfully'})

@app.route('/detect_signature_pages', methods=['POST'])
async def detect_signature_pages():
    data = request.get_json()  # Synchronous call
    pdf_path = data['pdf_path']
    pdf_reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(pdf_reader, pdf_path)
    return jsonify({'pages': pages})

@app.route('/extract_signature_pages', methods=['POST'])
async def extract_signature_pages():
    data = request.get_json()  # Synchronous call
    pdf_path = data['pdf_path']
    output_path = data['output_path']
    reader = PdfReader(pdf_path)
    pages = await signature_detector.detect_signature_pages(reader, pdf_path)

    # Create a temporary directory to ensure no tmp files are left behind
    with tempfile.TemporaryDirectory() as temp_output_dir:
        temp_pdf_path = os.path.join(temp_output_dir, "extracted_signatures.pdf")

        try:
            await signature_detector.extract_signature_pages(reader, pages, temp_pdf_path)

            # Move the final output to the specified output path
            shutil.move(temp_pdf_path, output_path)

            return jsonify(
                {'status': 'success', 'message': 'Signature pages extracted successfully', 'output_path': output_path})
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
    app.run(debug=True)
