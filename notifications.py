import os
from datetime import datetime

import os
from datetime import datetime


def get_notifications(page=1, per_page=10, output_folder=None):
    processed_files = []
    all_files = [filename for filename in os.listdir(output_folder) if filename.endswith('.pdf')]
    start = (page - 1) * per_page
    end = start + per_page
    paginated_files = all_files[start:end]

    for filename in paginated_files:
        num_signatures = filename.split("signatures")[0].split("_")[-1]

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
def get_all_files(output_folder=None):
    all_files = [os.path.join(output_folder, filename) for filename in os.listdir(output_folder) if
                 filename.endswith('.pdf')]
    return all_files
