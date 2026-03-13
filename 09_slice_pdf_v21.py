import os
import sys
from PyPDF2 import PdfReader, PdfWriter

slidesfiles = ["slides_oai.pdf", "slides_dsk.pdf", "slides_gemini.pdf"]

slidesfile = None
for f in slidesfiles:
    if os.path.isfile(f):
        slidesfile = f
        break

if not slidesfile or not os.path.isfile(slidesfile):
    print("Warning: No slide PDF found. Check again.")
    sys.exit(1)

print("slidesfile:", slidesfile)
print(f"Found the source file {slidesfile}")

try:
    with open(slidesfile, "rb") as input_pdf_file:
        pdf_reader = PdfReader(input_pdf_file)

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            pdf_writer = PdfWriter()
            pdf_writer.add_page(page)

            output_filename = f"slide{page_num + 1}.pdf"

            with open(output_filename, "wb") as output_pdf_file:
                pdf_writer.write(output_pdf_file)

            print(f"Slide {page_num + 1} saved to: {output_filename}")

    print(f"\nSuccessfully split '{slidesfile}' into individual slides")

except Exception as e:
    print(f"An error occurred while splitting PDF: {e}")