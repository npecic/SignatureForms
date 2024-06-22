import os
import shutil
import fitz  # PyMuPDF
import cv2
import numpy as np
import logging

def compare_pdfs(pdf1_path, pdf2_path, mismatch_text=None):
    """Compare two PDF files and return True if their entire text content is the same, else False.
    Optionally, capture a screenshot with bounding boxes around areas that don't match."""
    doc1 = fitz.open(pdf1_path)
    doc2 = fitz.open(pdf2_path)

    if len(doc1) != len(doc2):
        # logging.debug(f'PDF length mismatch: {len(doc1)} != {len(doc2)}')
        return False, False

    text_match = True
    pixmap_match = True

    for page_num in range(len(doc1)):
        page1 = doc1.load_page(page_num)
        page2 = doc2.load_page(page_num)

        # Get page text
        text1 = page1.get_text()
        text2 = page2.get_text()

        if text1 != text2:
            text_match = False
            # logging.debug(f'Text mismatch on page {page_num + 1}')

            if mismatch_text and (mismatch_text in text1 or mismatch_text in text2):
                text_match = False

        pix1 = page1.get_pixmap()
        pix2 = page2.get_pixmap()

        if pix1.samples != pix2.samples:
            pixmap_match = False
            # logging.debug(f'Pixmap mismatch on page {page_num + 1}')

            # Convert pixmap to numpy arrays
            img1 = np.frombuffer(pix1.samples, dtype=np.uint8).reshape(pix1.h, pix1.w, pix1.n)
            img2 = np.frombuffer(pix2.samples, dtype=np.uint8).reshape(pix2.h, pix2.w, pix2.n)

            # Convert numpy arrays to cv::UMat
            img1_cv = cv2.UMat(img1)
            img2_cv = cv2.UMat(img2)

            # Find differences using image processing
            diff_img = cv2.absdiff(img1_cv, img2_cv)
            diff_gray = cv2.cvtColor(diff_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

            # Find contours and draw bounding boxes around differences
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Find bounding boxes for all significant contours
            bounding_boxes = []
            size_threshold = 100
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w * h > size_threshold:
                    bounding_boxes.append([x, y, x + w, y + h])

            # Function to merge overlapping and adjacent bounding boxes
            def merge_boxes(boxes, distance_threshold=10):
                if not boxes:
                    return []

                merged_boxes = []
                while boxes:
                    current_box = boxes.pop(0)
                    merged = False
                    for i, merged_box in enumerate(merged_boxes):
                        if (current_box[0] <= merged_box[2] + distance_threshold and
                                current_box[2] >= merged_box[0] - distance_threshold and
                                current_box[1] <= merged_box[3] + distance_threshold and
                                current_box[3] >= merged_box[1] - distance_threshold):
                            # Merge the boxes
                            merged_boxes[i] = [
                                min(merged_box[0], current_box[0]),
                                min(merged_box[1], current_box[1]),
                                max(merged_box[2], current_box[2]),
                                max(merged_box[3], current_box[3])
                            ]
                            merged = True
                            break
                    if not merged:
                        merged_boxes.append(current_box)

                return merged_boxes

            # Merge overlapping bounding boxes
            merged_boxes = merge_boxes(bounding_boxes)
            # logging.debug(f'Bounding boxes on page {page_num + 1}: {merged_boxes}')

            # Draw the merged bounding boxes on the image
            img2_with_boxes = img2.copy()
            for box in merged_boxes:
                cv2.rectangle(img2_with_boxes, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)

            # Save the original image
            original_dir = 'static/manual_compare_img/original'
            if not os.path.exists(original_dir):
                os.makedirs(original_dir)
            original_path = os.path.join(original_dir,
                                         os.path.splitext(os.path.basename(pdf1_path))[0] + f'_Page_{page_num + 1}.png')
            cv2.imwrite(original_path, img1)

            # Save the image with bounding boxes
            screenshot_dir = 'static/manual_compare_img/bounding_screenshot'
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
            screenshot_path = os.path.join(screenshot_dir, os.path.splitext(os.path.basename(pdf2_path))[0] + f'_Page_{page_num + 1}.png')
            cv2.imwrite(screenshot_path, img2_with_boxes)

    return text_match, pixmap_match

def compare_pdf_folders(folder1, folder2, mismatch_dir, match_dir):
    mismatches = []
    matches = []
    folder2_files = {os.path.basename(file): os.path.join(root, file) for root, _, files in os.walk(folder2) for file in files if file.endswith('.pdf')}

    for root, _, files in os.walk(folder1):
        for file in files:
            if file.endswith('.pdf'):
                file1 = os.path.join(root, file)
                file2 = folder2_files.get(file)
                if file2:
                    text_match, pixmap_match = compare_pdfs(file1, file2)
                    if text_match and pixmap_match:
                        match_path = os.path.join(match_dir, file)
                        shutil.copyfile(file2, match_path)
                        matches.append({
                            "title": "Matched File",
                            "message": f"{file}",
                            "download_link": file
                        })
                        # logging.debug(f'Match found: {file1} == {file2}')
                    else:
                        mismatch_path = os.path.join(mismatch_dir, file)
                        shutil.copyfile(file2, mismatch_path)
                        mismatches.append({
                            "title": "Mismatched File",
                            "message": f"{file}",
                            "download_link": file
                        })
                        # logging.debug(f'Mismatch found: {file1} != {file2}')
                else:
                    logging.debug(f'File missing in folder2: {file}')

    return {"matches": matches, "mismatches": mismatches}

