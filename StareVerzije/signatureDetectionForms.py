import os
import logging
from PyPDF2 import PdfReader, PdfWriter
import argparse

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_pdfs(directory, password=None):
    """Load PDF files from the specified directory and decrypt if necessary."""
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    pdf_readers = {}

    for pdf_file in pdf_files:
        path = os.path.join(directory, pdf_file)
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                if password:
                    reader.decrypt(password)
                else:
                    logging.warning(f"PDF {pdf_file} is encrypted but no password was provided.")
                    continue
            pdf_readers[pdf_file] = reader
        except Exception as e:
            logging.error(f"Error loading PDF {pdf_file}: {e}")

    return pdf_readers


def detect_signature_pages(pdf_reader):
    """Detect pages containing signature keywords in a given PDF reader object."""
    signature_pages = []

    for page_num in range(len(pdf_reader.pages)):
        try:
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text and any(keyword in text.lower() for keyword in ['signature', 'signed', 'authorized', 'sign']):
                signature_pages.append(page_num)
        except Exception as e:
            logging.error(f"Error processing page {page_num} in PDF: {e}")

    return signature_pages


def extract_signature_pages(pdf_reader, page_numbers, output_path):
    """Extract specified pages from a PDF reader object and save them to a new PDF file."""
    pdf_writer = PdfWriter()

    for page_num in page_numbers:
        pdf_writer.add_page(pdf_reader.pages[page_num])

    try:
        with open(output_path, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)
        logging.info(f"Extracted pages {page_numbers} to {output_path}")
    except Exception as e:
        logging.error(f"Error writing extracted pages to {output_path}: {e}")


def main():
    """Main function to parse arguments and process PDFs."""
    parser = argparse.ArgumentParser(description="Extract signature pages from PDF files.")
    parser.add_argument("input_directory", help="Path to the input directory containing PDF files.")
    parser.add_argument("output_directory", help="Path to the output directory for extracted pages.")
    parser.add_argument("--password", help="Password for encrypted PDF files.", default=None)
    args = parser.parse_args()

    input_directory = args.input_directory
    output_directory = args.output_directory
    password = args.password

    os.makedirs(output_directory, exist_ok=True)

    pdfs = load_pdfs(input_directory, password)
    signature_pages = {pdf: detect_signature_pages(pdfs[pdf]) for pdf in pdfs}

    for pdf_file, pages in signature_pages.items():
        if pages:
            output_path = os.path.join(output_directory, f'signature_pages_{pdf_file}')
            extract_signature_pages(pdfs[pdf_file], pages, output_path)

    results = {pdf: pages for pdf, pages in signature_pages.items() if pages}
    print("Summary of PDFs with signature pages:")
    for pdf, pages in results.items():
        print(f"{pdf}: Pages {pages}")


if __name__ == "__main__":
    main()