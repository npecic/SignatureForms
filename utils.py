import os
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle


def get_all_files(output_folder):
    all_files = [os.path.join(output_folder, filename) for filename in os.listdir(output_folder) if
                 filename.endswith('.pdf')]
    return all_files


def extract_num_signatures(filename):
    return int(filename.split("_")[-2])  # Extracting num_signatures from the filename


def generate_pdf(processed_files, output_folder):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Set up the table style
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),  # Header background color
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Center align all cells
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Header font
        ("FONTSIZE", (0, 0), (-1, 0), 12),  # Header font size
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Header bottom padding
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),  # Alternate row background color
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),  # Alternate row text color
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),  # Cell font
        ("FONTSIZE", (0, 1), (-1, -1), 10),  # Cell font size
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Center align all cells vertically
        ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Add grid lines
        ("ALIGN", (1, 1), (1, -1), "LEFT"),  # Left align the "File Name" column
    ])

    # Set up the table data
    table_data = [["Number", "File Name", "Date Processed", "Signatures"]]

    for idx, file in enumerate(processed_files, start=1):
        # Get processed time using the same logic as in notifications
        processed_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(output_folder, file["title"])))

        # Set color to red only for the signature number
        signature_num = str(extract_num_signatures(file["title"]))
        signature_num_color = "#FF0000" if signature_num != "0" else "#000000"  # Red for non-zero, black for zero

        # Concatenate the file name if it exceeds a certain count
        if len(file["title"]) > 58:
            file_name = file["title"][:58] + "..."
        else:
            file_name = file["title"]

        table_data.append([str(idx), file_name, processed_time.strftime("%Y-%m-%d %H:%M:%S"), signature_num])

        # Check if the table is about to exceed the available space on the current page
        if len(table_data) > 35:
            # Create the table
            table = Table(table_data, colWidths=[0.7 * inch, 4.5 * inch, 1.5 * inch, 1 * inch])  # Adjust column widths
            table.setStyle(table_style)

            # Draw the table on the canvas
            table.wrapOn(c, width, height)
            table.drawOn(c, 30, height - 65 - table._height)  # Adjust the starting position for the table

            # Add a modern title
            c.setFont("Helvetica-Bold", 24)
            c.setFillColorRGB(0, 0, 0.5)  # Dark blue color
            c.drawString(30, height - 40, "Processed Files Report")

            c.showPage()  # Start a new page

            # Reset the table data for the next page
            table_data = [["Number", "File Name", "Date Processed", "Signatures"]]

        # Create the table for the remaining data
    if len(table_data) > 1:  # Check if there are remaining rows to display
        table = Table(table_data, colWidths=[0.7 * inch, 4.5 * inch, 1.5 * inch, 1 * inch])  # Adjust column widths
        table.setStyle(table_style)

        # Draw the table on the canvas
        table.wrapOn(c, width, height)
        table.drawOn(c, 30, height - 60 - table._height)  # Adjust the starting position for the table

    c.save()
    buffer.seek(0)
    return buffer