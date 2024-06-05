# notifications.py
import os
from datetime import datetime

def get_notifications(page=1, per_page=10, output_folder=None):
    processed_files = []
    all_files = [filename for filename in os.listdir(output_folder) if filename.endswith('.pdf')]
    start = (page - 1) * per_page
    end = start + per_page
    paginated_files = all_files[start:end]

    for filename in paginated_files:
        num_signatures = filename.split('_')[0]  # Extract number of signatures from filename
        num_signatures = num_signatures.split('signatures')[0]  # Remove '_signatures' from the count
        processed_files.append({
            "title": "File Processed",
            "message": f"{filename}. {num_signatures} signature(s) is/are ready for download.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Use current timestamp
            "download_link": filename
        })

    total_files = len(all_files)
    total_pages = (total_files + per_page - 1) // per_page  # Calculate total pages
    return processed_files, total_pages

def get_all_files(output_folder=None):
    all_files = [os.path.join(output_folder, filename) for filename in os.listdir(output_folder) if filename.endswith('.pdf')]
    return all_files
