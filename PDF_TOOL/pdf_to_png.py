import fitz  # PyMuPDF
from PIL import Image
import os


def pdf_to_images(pdf_path, output_folder):
    # Open the PDF file
    document = fitz.open(pdf_path)

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Loop through each page
    for page_num in range(len(document)):
        # Load the page
        page = document.load_page(page_num)
        # Render the page to an image
        pix = page.get_pixmap()

        # Define the output image path
        image_path = os.path.join(output_folder,
                                  f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page_num + 1}.png")

        # Save the image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(image_path)

        print(f"Saved {image_path}")

    print(f"Processed {pdf_path}")


def process_pdfs_in_folder(folder_path, output_folder):
    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        # Check if the file is a PDF
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            pdf_output_folder = os.path.join(output_folder, os.path.splitext(filename)[0])
            pdf_to_images(pdf_path, pdf_output_folder)


if __name__ == "__main__":
    input_folder = "pdf"  # Replace with the path to your folder containing PDFs
    output_folder = "pdf/output"  # Replace with the path to your output folder

    process_pdfs_in_folder(input_folder, output_folder)
