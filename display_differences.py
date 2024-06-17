import os
import fitz  # PyMuPDF
import shutil
import hashlib
import logging
from multiprocessing import Pool, cpu_count
from functools import partial

# Configure logging with an option to set the level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def hash_file(file_path):
    """
    Generate SHA-256 hash of the file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: SHA-256 hash of the file.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def hash_image(image):
    """
    Generate SHA-256 hash of an image.

    Args:
        image (bytes): Image data.

    Returns:
        str: SHA-256 hash of the image.
    """
    hash_sha256 = hashlib.sha256(image)
    return hash_sha256.hexdigest()

def compare_texts(text1, text2):
    """
    Compare two text strings and return True if they are the same, else False.

    Args:
        text1 (str): First text string.
        text2 (str): Second text string.

    Returns:
        bool: True if texts are the same, False otherwise.
    """
    return text1 == text2

def extract_text_and_images(pdf_path):
    """
    Extract text and images from a PDF file.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        tuple: Extracted text and a list of image hashes.
    """
    doc = fitz.open(pdf_path)
    text = ""
    image_hashes = []

    for page in doc:
        text += page.get_text()

        for image in page.get_images(full=True):
            xref = image[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_hash = hash_image(image_bytes)
            image_hashes.append(image_hash)

    doc.close()
    return text, image_hashes

def compare_pdfs(pdf1_path, pdf2_path):
    """
    Compare two PDF files and return True if they are the same, else False.

    Args:
        pdf1_path (str): Path to the first PDF file.
        pdf2_path (str): Path to the second PDF file.

    Returns:
        bool: True if PDFs are the same, False otherwise.
    """
    try:
        doc1 = fitz.open(pdf1_path)
        doc2 = fitz.open(pdf2_path)

        if len(doc1) != len(doc2):
            logging.info(f"Number of pages mismatch between {pdf1_path} and {pdf2_path}")
            return False

        for page_num in range(len(doc1)):
            page1 = doc1.load_page(page_num)
            page2 = doc2.load_page(page_num)

            if page1.get_text() != page2.get_text():
                logging.info(f"Text content mismatch on page {page_num+1} between {pdf1_path} and {pdf2_path}")
                # Render pages to find differences
                pix1 = page1.get_pixmap()
                pix2 = page2.get_pixmap()

                # Find differences
                diff_area = pix1.extract_difference(pix2)

                # Add bounding box around differences
                for r in diff_area:
                    page1.add_rect(r, color=(1, 0, 0), width=2)

                # Save the modified page with bounding boxes
                page1.save(os.path.join(mismatch_dir, f"mismatch_page_{page_num+1}.pdf"))

                doc1.close()
                doc2.close()
                return False

        doc1.close()
        doc2.close()
        return True

    except Exception as e:
        logging.error(f"Error comparing {pdf1_path} and {pdf2_path}: {e}")
        return False

def process_file_pair(folder1, folder2, mismatch_dir, pdf_file):
    """
    Process a pair of PDF files and determine if they match.

    Args:
        folder1 (str): Path to the first folder.
        folder2 (str): Path to the second folder.
        mismatch_dir (str): Path to the mismatch directory.
        pdf_file (str): PDF file name.

    Returns:
        dict: Information about mismatched files if any.
    """
    pdf1_path = os.path.join(folder1, pdf_file)
    pdf2_path = os.path.join(folder2, pdf_file)

    try:
        # Quick hash comparison before detailed comparison
        if hash_file(pdf1_path) == hash_file(pdf2_path):
            return None

        if not compare_pdfs(pdf1_path, pdf2_path):
            shutil.copy(pdf2_path, os.path.join(mismatch_dir, pdf_file))
            logging.info(f"Mismatch found: {pdf_file}")
            return {
                "title": "Mismatched File",
                "message": f"{pdf_file}",
                "download_link": pdf_file
            }
    except Exception as e:
        logging.error(f"Error comparing {pdf1_path} and {pdf2_path}: {e}")

    return None

def compare_pdf_folders(folder1, folder2, mismatch_dir, logging_level=logging.INFO):
    """
    Compare PDF files in two folders and copy mismatches to the mismatch directory.

    Args:
        folder1 (str): Path to the first folder containing PDF files.
        folder2 (str): Path to the second folder containing PDF files.
        mismatch_dir (str): Path to the directory where mismatched files will be copied.
        logging_level (int): Logging level (default: logging.INFO).

    Returns:
        list: List of dictionaries with information about mismatched files.
    """
    logging.getLogger().setLevel(logging_level)

    if not os.path.exists(mismatch_dir):
        os.makedirs(mismatch_dir)

    folder1_files = set(f for f in os.listdir(folder1) if f.lower().endswith('.pdf'))
    folder2_files = set(f for f in os.listdir(folder2) if f.lower().endswith('.pdf'))

    common_files = folder1_files & folder2_files

    mismatches = []

    # Use multiprocessing to compare files in parallel
    with Pool(cpu_count()) as pool:
        process_partial = partial(process_file_pair, folder1, folder2, mismatch_dir)
        results = pool.map(process_partial, common_files)

    mismatches = [result for result in results if result is not None]

    return mismatches

# Example usage
if __name__ == "__main__":
    folder1 = "test/real"
    folder2 = "test/fake"
    mismatch_dir = "test/output"

    mismatches = compare_pdf_folders(folder1, folder2, mismatch_dir, logging.DEBUG)
    for mismatch in mismatches:
        print(mismatch)