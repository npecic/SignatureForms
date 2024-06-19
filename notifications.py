import os
from datetime import datetime

async def get_notifications(page=1, per_page=10, output_folder=None):
    processed_files = []
    all_files = [filename for filename in os.listdir(output_folder) if filename.endswith('.pdf')]
    start = (page - 1) * per_page
    end = start + per_page
    paginated_files = all_files[start:end]

    for filename in paginated_files:
        # Extracting num_signatures from the filename
        num_signatures = int(filename.split("_")[-2])

        try:
            processed_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(output_folder, filename)))
        except FileNotFoundError:
            continue

        processed_files.append({
            "title": "File Processed",
            "message": f"{filename}.",
            "timestamp": processed_time.strftime("%Y-%m-%d %H:%M:%S"),
            "signature": f"{num_signatures}",
            "download_link": filename
        })

    total_pages = len(all_files) // per_page + (1 if len(all_files) % per_page > 0 else 0)
    return processed_files, total_pages

async def get_all_notifications(output_folder=None):
    processed_files = []
    all_files = [filename for filename in os.listdir(output_folder) if filename.endswith('.pdf')]

    for filename in all_files:
        num_signatures = int(filename.split("_")[-2])

        try:
            processed_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(output_folder, filename)))
        except FileNotFoundError:
            continue

        processed_files.append({
            "title": "File Processed",
            "message": f"{filename}.",
            "timestamp": processed_time.strftime("%Y-%m-%d %H:%M:%S"),
            "signature": f"{num_signatures}",
            "download_link": filename
        })

    return processed_files

def get_all_files(output_folder=None):
    all_files = [os.path.join(output_folder, filename) for filename in os.listdir(output_folder) if
                 filename.endswith('.pdf')]
    return all_files
