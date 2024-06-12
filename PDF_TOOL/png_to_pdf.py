from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os


def images_to_pdf(image_list, output_pdf_path):
    if not image_list:
        print("No images to convert.")
        return

    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    for image_path in image_list:
        img = Image.open(image_path)
        img_width, img_height = img.size

        # Calculate the position and size to fit the A4 page
        if img_width > img_height:
            img = img.rotate(90, expand=True)
            img_width, img_height = img.size

        width_ratio = A4[0] / img_width
        height_ratio = A4[1] / img_height
        ratio = min(width_ratio, height_ratio)
        img_width = int(img_width * ratio)
        img_height = int(img_height * ratio)

        x_offset = (A4[0] - img_width) / 2
        y_offset = (A4[1] - img_height) / 2

        c.drawImage(image_path, x_offset, y_offset, img_width, img_height)
        c.showPage()

    c.save()
    print(f"Saved merged PDF as {output_pdf_path}")


def process_images_in_folder(folder_path, output_pdf_path):
    image_list = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                  f.lower().endswith('.jpg') or f.lower().endswith('.png')]
    if not image_list:
        print("No JPG images found in the folder.")
        return

    print(f"Found {len(image_list)} images to process.")
    images_to_pdf(image_list, output_pdf_path)


if __name__ == "__main__":
    input_folder = "png"  # Replace with the path to your folder containing JPG images
    output_pdf_path = "output/merged.pdf"  # Replace with the path to your output PDF file

    if not os.path.exists("output"):
        os.makedirs("output")

    process_images_in_folder(input_folder, output_pdf_path)
