import os
import shutil
import fitz  # PyMuPDF
import cv2
import numpy as np
import logging
from difflib import SequenceMatcher
import pytesseract
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ThreadPoolExecutor, as_completed
import configparser

# Configurable Parameters
config = configparser.ConfigParser()
config.read('data/config.ini')
text_similarity_threshold = float(config['DEFAULT']['TextSimilarityThreshold'])
image_similarity_threshold = float(config['DEFAULT']['ImageSimilarityThreshold'])
ocr_language = config['DEFAULT']['OCRLanguage']
batch_size = int(config['DEFAULT']['BatchSize'])
max_workers = int(config['DEFAULT']['MaxWorkers'])

# Configure Logging
logging.basicConfig(level=logging.DEBUG, filename='pdf_compare.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')


def text_similarity(text1, text2):
    return SequenceMatcher(None, text1, text2).ratio()


def extract_text_with_ocr(image):
    try:
        return pytesseract.image_to_string(Image.fromarray(image), lang=ocr_language)
    except Exception as e:
        logging.error(f"Error in OCR extraction: {e}")
        return ""


def compare_images(image1, image2):
    try:
        if image1.ndim == 2:
            gray1 = image1
        elif image1.shape[2] == 3:
            gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        elif image1.shape[2] == 4:
            gray1 = cv2.cvtColor(image1, cv2.COLOR_BGRA2GRAY)
        else:
            logging.error(f"Invalid number of channels in input image1: {image1.shape}")
            return 0

        if image2.ndim == 2:
            gray2 = image2
        elif image2.shape[2] == 3:
            gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        elif image2.shape[2] == 4:
            gray2 = cv2.cvtColor(image2, cv2.COLOR_BGRA2GRAY)
        else:
            logging.error(f"Invalid number of channels in input image2: {image2.shape}")
            return 0

        score, _ = ssim(gray1, gray2, full=True)
        return score
    except Exception as e:
        logging.error(f"Error comparing images: {e}")
        return 0


def compare_pdfs(pdf1_path, pdf2_path, mismatch_text=None):
    try:
        doc1 = fitz.open(pdf1_path)
        doc2 = fitz.open(pdf2_path)

        if len(doc1) != len(doc2):
            logging.warning(f"Mismatch in number of pages: {pdf1_path} vs {pdf2_path}")
            return False, False

        text_match = True
        pixmap_match = True

        for page_num in range(len(doc1)):
            page1 = doc1.load_page(page_num)
            page2 = doc2.load_page(page_num)

            # Get page text
            text1 = page1.get_text()
            text2 = page2.get_text()

            # Check text similarity
            similarity = text_similarity(text1, text2)
            if similarity < text_similarity_threshold:
                text_match = False

            # Increase resolution for better clarity
            zoom_x = 2.0  # horizontal zoom
            zoom_y = 2.0  # vertical zoom
            mat = fitz.Matrix(zoom_x, zoom_y)

            pix1 = page1.get_pixmap(matrix=mat)
            pix2 = page2.get_pixmap(matrix=mat)

            if pix1.samples != pix2.samples:
                pixmap_match = False

                # Convert pixmap to numpy arrays
                img1 = np.frombuffer(pix1.samples, dtype=np.uint8).reshape(pix1.h, pix1.w, pix1.n)
                img2 = np.frombuffer(pix2.samples, dtype=np.uint8).reshape(pix2.h, pix2.w, pix2.n)

                # Compare images using SSIM
                similarity_score = compare_images(img1, img2)
                if similarity_score < image_similarity_threshold:
                    pixmap_match = False

                # Find differences using image processing
                diff_img = cv2.absdiff(img1, img2)
                diff_gray = cv2.cvtColor(diff_img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

                # Find contours and draw bounding boxes around differences
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Find bounding boxes for all significant contours
                bounding_boxes = []
                size_threshold = 20
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w * h > size_threshold:
                        bounding_boxes.append([x, y, x + w, y + h])

                # Function to merge overlapping and adjacent bounding boxes
                def merge_boxes(boxes, distance_threshold=30):
                    merged = True
                    while merged:
                        merged = False
                        new_boxes = []
                        while boxes:
                            box1 = boxes.pop(0)
                            for i, box2 in enumerate(boxes):
                                if (box1[0] <= box2[2] + distance_threshold and
                                        box1[2] >= box2[0] - distance_threshold and
                                        box1[1] <= box2[3] + distance_threshold and
                                        box1[3] >= box2[1] - distance_threshold):
                                    box2 = [
                                        min(box1[0], box2[0]),
                                        min(box1[1], box2[1]),
                                        max(box1[2], box2[2]),
                                        max(box1[3], box2[3])
                                    ]
                                    boxes[i] = box2
                                    merged = True
                                    break
                            else:
                                new_boxes.append(box1)
                        boxes = new_boxes
                    return boxes

                # Merge overlapping bounding boxes
                merged_boxes = merge_boxes(bounding_boxes)

                # Enlarge bounding boxes
                def enlarge_boxes(boxes, enlargement=5):
                    enlarged_boxes = []
                    for box in boxes:
                        x1, y1, x2, y2 = box
                        enlarged_boxes.append([
                            max(0, x1 - enlargement),
                            max(0, y1 - enlargement),
                            min(img2.shape[1], x2 + enlargement),
                            min(img2.shape[0], y2 + enlargement)
                        ])
                    return enlarged_boxes

                enlarged_boxes = enlarge_boxes(merged_boxes)

                # Draw the enlarged bounding boxes and arrows on the image
                img2_with_boxes = img2.copy()
                for box in enlarged_boxes:
                    x1, y1, x2, y2 = box
                    cv2.rectangle(img2_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2

                    # Arrow properties
                    arrow_length = 150  # Adjust this value to change arrow size
                    arrow_offset = 20  # Adjust this value to change arrow distance from bounding box
                    arrow_start_x, arrow_start_y = x2 + arrow_offset + arrow_length, center_y
                    arrow_end_x, arrow_end_y = x2 + arrow_offset, center_y

                    # Draw arrow from right to bounding box
                    cv2.arrowedLine(img2_with_boxes, (arrow_start_x, arrow_start_y), (arrow_end_x, arrow_end_y),
                                    (0, 0, 255), 4)

                # Save the original image
                original_dir = 'static/manual_compare_img/original'
                if not os.path.exists(original_dir):
                    os.makedirs(original_dir)
                original_path = os.path.join(original_dir,
                                             os.path.splitext(os.path.basename(pdf1_path))[
                                                 0] + f'_Page_{page_num + 1}.png')
                cv2.imwrite(original_path, img1)

                # Save the image with bounding boxes
                screenshot_dir = 'static/manual_compare_img/bounding_screenshot'
                if not os.path.exists(screenshot_dir):
                    os.makedirs(screenshot_dir)
                screenshot_path = os.path.join(screenshot_dir, os.path.splitext(os.path.basename(pdf2_path))[
                    0] + f'_Page_{page_num + 1}.png')
                cv2.imwrite(screenshot_path, img2_with_boxes)

        return text_match, pixmap_match
    except Exception as e:
        logging.exception(f"Error comparing PDFs: {pdf1_path} vs {pdf2_path}")
        return False, False


def compare_single_file_pair(args):
    file1, file2, mismatch_dir, match_dir = args
    try:
        text_match, pixmap_match = compare_pdfs(file1, file2)
        if text_match and pixmap_match:
            match_path = os.path.join(match_dir, os.path.basename(file1))
            if not os.path.exists(match_path):  # Avoid redundant writes
                shutil.copyfile(file2, match_path)
            return "match", os.path.basename(file1)
        else:
            mismatch_path = os.path.join(mismatch_dir, os.path.basename(file1))
            if not os.path.exists(mismatch_path):  # Avoid redundant writes
                shutil.copyfile(file2, mismatch_path)
            return "mismatch", os.path.basename(file1)
    except Exception as e:
        logging.exception(f"Error comparing file pair: {file1} and {file2}")
        return "error", os.path.basename(file1)


def compare_pdf_folders_in_parallel(folder1, folder2, mismatch_dir, match_dir):
    mismatches = []
    matches = []
    errors = []
    folder2_files = {os.path.basename(file): os.path.join(root, file) for root, _, files in os.walk(folder2) for file in
                     files if file.endswith('.pdf')}
    file_pairs = [(os.path.join(root, file), folder2_files[file], mismatch_dir, match_dir) for root, _, files in
                  os.walk(folder1) for file in files if file.endswith('.pdf') and file in folder2_files]

    # Log if files are found or not in folders
    folder1_files = [os.path.join(root, file) for root, _, files in os.walk(folder1) for file in files if
                     file.endswith('.pdf')]
    folder2_files_check = [os.path.join(root, file) for root, _, files in os.walk(folder2) for file in files if
                           file.endswith('.pdf')]

    if not folder1_files:
        logging.warning("No files found in folder1.")
    else:
        logging.info(f"Found {len(folder1_files)} files in folder1.")

    if not folder2_files_check:
        logging.warning("No files found in folder2.")
    else:
        logging.info(f"Found {len(folder2_files_check)} files in folder2.")

    # Log which files were not found in the second folder
    for root, _, files in os.walk(folder1):
        for file in files:
            if file.endswith('.pdf') and file not in folder2_files:
                logging.warning(f"File {file} from folder1 not found in folder2.")

    if not file_pairs:
        logging.warning("No matching files found in folder1 or folder2.")
    else:
        logging.info(f"Found {len(file_pairs)} matching files to compare.")

    for i in range(0, len(file_pairs), batch_size):
        batch = file_pairs[i:i + batch_size]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file_pair = {executor.submit(compare_single_file_pair, file_pair): file_pair for file_pair in
                                   batch}
            for future in as_completed(future_to_file_pair):
                try:
                    result, file = future.result()
                    if result == "match":
                        matches.append({
                            "title": "Matched File",
                            "message": file,
                            "download_link": file
                        })
                    elif result == "mismatch":
                        mismatches.append({
                            "title": "Mismatched File",
                            "message": file,
                            "download_link": file
                        })
                    else:
                        errors.append({
                            "title": "Error File",
                            "message": file,
                            "download_link": file
                        })
                except Exception as e:
                    logging.error(f"Error processing future result: {future_to_file_pair[future]} - {e}")

    return {"matches": matches, "mismatches": mismatches, "errors": errors}
