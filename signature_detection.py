import json
import re
import logging
from PyPDF2 import PdfReader, PdfWriter
from pytesseract import image_to_string
from pdf2image import convert_from_path


class SignatureDetector:
    def __init__(self):
        self.primary_keywords = []
        self.secondary_keywords = []
        self.load_default_keywords()

    def set_keywords(self, primary_keywords, secondary_keywords):
        """Set the primary and secondary keywords."""
        self.primary_keywords = primary_keywords
        self.secondary_keywords = secondary_keywords

    def load_default_keywords(self):
        """Load default keywords from the JSON file."""
        self.set_keywords_from_json('data/defaultKeywords.json')

    def set_keywords_from_json(self, json_path):
        """Load keywords from a JSON file."""
        with open(json_path, 'r') as file:
            data = json.load(file)
        self.primary_keywords = data.get('primary_keywords', [])
        self.secondary_keywords = data.get('secondary_keywords', [])

    def save_keywords_to_json(self, json_path, primary_keywords, secondary_keywords):
        """Save keywords to a JSON file."""
        with open(json_path, 'w') as file:
            json.dump({
                'primary_keywords': primary_keywords,
                'secondary_keywords': secondary_keywords
            }, file)

    @property
    def primary_keyword_patterns(self):
        """Compile primary keywords into regex patterns."""
        return [re.compile(re.escape(keyword)) for keyword in self.primary_keywords]

    @property
    def secondary_keyword_patterns(self):
        """Compile secondary keywords into regex patterns."""
        return [re.compile(re.escape(keyword)) for keyword in self.secondary_keywords]

    def detect_signature_pages(self, pdf_reader, pdf_path):
        signature_pages = []

        for page_num in range(len(pdf_reader.pages)):
            try:
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text = text.strip()
                    primary_keyword_matched = any(pattern.search(text) for pattern in self.primary_keyword_patterns)
                    if primary_keyword_matched:
                        secondary_keyword_matched = any(
                            secondary_keyword.lower() in text.lower() for secondary_keyword in self.secondary_keywords)
                        if not secondary_keyword_matched:
                            signature_pages.append(page_num)
                else:
                    images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
                    for image in images:
                        ocr_text = image_to_string(image).strip()
                        primary_keyword_matched = any(
                            pattern.search(ocr_text) for pattern in self.primary_keyword_patterns)
                        if primary_keyword_matched:
                            secondary_keyword_matched = any(
                                secondary_keyword.lower() in ocr_text.lower() for secondary_keyword in
                                self.secondary_keywords)
                            if not secondary_keyword_matched:
                                signature_pages.append(page_num)
            except Exception as e:
                logging.error(f"Error processing page {page_num} in PDF: {e}")

        return signature_pages

    def extract_signature_pages(self, reader, page_nums, output_filepath):
        writer = PdfWriter()
        for page_num in page_nums:
            writer.add_page(reader.pages[page_num])
        with open(output_filepath, 'wb') as output_pdf:
            writer.write(output_pdf)

# Create an instance of the SignatureDetector
signature_detector = SignatureDetector()