#app.py
from PyPDF2 import PdfFileReader
from flask import Flask, redirect, url_for, render_template, send_from_directory, request, send_file, jsonify
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, SECRET_KEY
from notifications import get_notifications, get_all_files
from upload import upload_file
from signature_detection import signature_detector
import zipfile
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.secret_key = SECRET_KEY  # Required for flashing messages


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


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


@app.route('/download-all')
def download_all():
    from notifications import get_all_files  # Import inside the function to avoid circular import
    all_files = get_all_files(app.config['OUTPUT_FOLDER'])
    with zipfile.ZipFile('all_files.zip', 'w') as zipf:
        for file in all_files:
            zipf.write(file, os.path.basename(file))
    return send_file('all_files.zip', as_attachment=True)


@app.route('/set_keywords', methods=['POST'])
def set_keywords():
    data = request.json
    keyword_option = data.get('keyword_option')

    if keyword_option == 'default':
        signature_detector.load_default_keywords()
    else:
        primary_keywords = ','.join(data.get('primary_keywords', []))
        secondary_keywords = ','.join(data.get('secondary_keywords', []))
        signature_detector.set_keywords(primary_keywords.split(','), secondary_keywords.split(','))
        signature_detector.save_keywords_to_json('manualKeywords.json', primary_keywords.split(','), secondary_keywords.split(','))

    return jsonify({'message': 'Keywords updated successfully'})

@app.route('/detect_signature_pages', methods=['POST'])
def detect_signature_pages():
    data = request.json
    pdf_path = data['pdf_path']
    pages = signature_detector.detect_signature_pages(pdf_path)
    return jsonify({'pages': pages})


@app.route('/extract_signature_pages', methods=['POST'])
def extract_signature_pages():
    data = request.json
    pdf_path = data['pdf_path']
    output_path = data['output_path']
    reader = PdfFileReader(pdf_path)
    pages = signature_detector.detect_signature_pages(pdf_path)
    signature_detector.extract_signature_pages(reader, pages, output_path)
    return jsonify(
        {'status': 'success', 'message': 'Signature pages extracted successfully', 'output_path': output_path})


@app.route('/export-file-names')
def export_file_names():
    all_files = get_all_files(output_folder=app.config['OUTPUT_FOLDER'])
    file_names = [os.path.basename(file) for file in all_files]
    csv_content = "File Name, Date Processed, Signatures Found\n"

    for file in file_names:
        num_signatures = file.split('_')[0]  # Extract number of signatures from filename
        csv_content += f"{file},2024-06-05\n"  # Replace with actual date processing logic

    response = jsonify({'csv': csv_content})
    response.headers['Content-Disposition'] = 'attachment; filename=processed_files.csv'
    response.mimetype = 'text/csv'
    return response


if __name__ == '__main__':
    app.run(debug=True)