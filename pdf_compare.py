import os
import fitz  # PyMuPDF
import shutil
from datetime import datetime

def compare_pdfs(pdf1_path, pdf2_path):
    """Compare two PDF files and return True if they are the same, else False."""
    doc1 = fitz.open(pdf1_path)
    doc2 = fitz.open(pdf2_path)

    if len(doc1) != len(doc2):
        return False

    for page_num in range(len(doc1)):
        page1 = doc1.load_page(page_num)
        page2 = doc2.load_page(page_num)

        pix1 = page1.get_pixmap()
        pix2 = page2.get_pixmap()

        if pix1.samples != pix2.samples:
            return False

    return True

def compare_pdf_folders(folder1, folder2, mismatch_dir):
    """Compare PDF files in two folders and copy mismatches to the mismatch directory."""
    if not os.path.exists(mismatch_dir):
        os.makedirs(mismatch_dir)

    folder1_files = set(f for f in os.listdir(folder1) if f.lower().endswith('.pdf'))
    folder2_files = set(f for f in os.listdir(folder2) if f.lower().endswith('.pdf'))

    common_files = folder1_files & folder2_files

    mismatches = []
    for pdf_file in common_files:
        pdf1_path = os.path.join(folder1, pdf_file)
        pdf2_path = os.path.join(folder2, pdf_file)

        if not compare_pdfs(pdf1_path, pdf2_path):
            shutil.copy(pdf2_path, os.path.join(mismatch_dir, pdf_file))
            mismatches.append({
                "title": "Mismatched File",
                "message": f"{pdf_file}",
                "download_link": pdf_file
            })

    return mismatches
