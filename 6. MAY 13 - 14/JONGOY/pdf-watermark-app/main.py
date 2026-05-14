import os
from tkinter import Tk, filedialog, simpledialog
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

# ==========================================
# CREATE WATERMARK PDF (with ReportLab)
# ==========================================
def create_watermark(project_code):
    """
    Clean dense engineering watermark:
    - 45° rotation
    - 20% opacity
    - 2x more coverage than previous version
    - NO overlap, still structured grid
    """

    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    width, height = letter

    c.setFillColor(Color(0, 0, 0, alpha=0.2))
    c.setFont("Helvetica", 26)

    c.translate(width / 2, height / 2)
    c.rotate(45)

    # =========================
    # 2X DENSITY IMPROVEMENT
    # =========================
    # Previous:
    # step_x = 250, step_y = 120

    # Now reduced spacing = more occurrences
    step_x = 180
    step_y = 90

    # Expanded range = more rows + columns
    x_range = range(-1200, 1200, step_x)
    y_range = range(-1200, 1200, step_y)

    for x in x_range:
        for y in y_range:
            c.drawCentredString(x, y, project_code)

    c.save()
    packet.seek(0)

    return PdfReader(packet)


# ==========================================
# APPLY WATERMARK TO PDF
# ==========================================
def apply_watermark(input_pdf_path, output_pdf_path, project_code):
    """
    Applies watermark to all pages of input PDF
    """
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    watermark_pdf = create_watermark(project_code)
    watermark_page = watermark_pdf.pages[0]

    for page in reader.pages:
        # Merge watermark with original page
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)


# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    # Hide main tkinter window
    root = Tk()
    root.withdraw()

    print("Select a PDF file...")

    # File picker
    file_path = filedialog.askopenfilename(
        title="Select PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not file_path:
        print("No file selected.")
        return

    # Ask for project code
    project_code = simpledialog.askstring("Input", "Enter Project Code:")

    if not project_code:
        print("No project code entered.")
        return

    # Save output using the project code as filename
    directory = os.path.dirname(file_path)
    output_path = os.path.join(directory, f"{project_code}.pdf")

    print("Processing...")

    apply_watermark(file_path, output_path, project_code)

    print(f"Done! Saved as: {output_path}")


if __name__ == "__main__":
    main()