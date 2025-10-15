######### Packages ##################
import os, re, shutil
import json
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path

######### Input Files ##################
pdf_path = "source.pdf"  # Full textbook PDF
json_path = "subchapter_index_physical.json"
output_dir = "." # "subchapters_pdf"

######### Create Output Folders, If Needed ##################
os.makedirs(output_dir, exist_ok=True)

######### Load JSON Index ##################
with open(json_path, "r", encoding="utf-8") as f:
    subchapters = json.load(f)

######### Load PDF ##################
reader = PdfReader(pdf_path)
total_pages = len(reader.pages)
#print(f"Loaded {pdf_path} with {total_pages} pages")

######### Extract Each Subchapter and Save as PDF ##################
for entry in subchapters:
    title = entry["title"]
    # Adjust for printed numbering starting from e.g. 79
    first_printed = subchapters[0]["begin_physical"]  # e.g. 79
    start = entry["begin_physical"] - first_printed
    end = entry["end_physical"] - first_printed
    
    if start < 0:
        print(f"   ↪ start {start} < 0 → set to 0")
        start = 0
    if end >= total_pages:
        end = total_pages - 1
    if start >= total_pages:
        print(f"⚠️ Skipping '{title}': start {start} beyond end of document ({total_pages-1})")
    
    writer = PdfWriter()
    for i in range(start, end + 1):
        writer.add_page(reader.pages[i])
    
    # Determine output filename (supports 3.5, 3.5.1, 3.5.7, etc.)
    if "Problem Set" in title or "Practice Exercises" in title or "Problems" in title:
        chapter_num = title.split()[0]
        filename = f"{chapter_num}-problems.pdf"
    else:
        match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", title)
        if match:
            parts = [p for p in match.groups() if p]  # drop None
            filename = "-".join(parts) + ".pdf"
        else:
            slug = title.lower().replace(" ", "-").replace(".", "-")
            filename = f"{slug}.pdf"

    output_path = os.path.join(output_dir, filename)
    with open(output_path, "wb") as f:
        writer.write(f)

########## Move PDFs into Chapter and Subchapter Folders #########
for filename in os.listdir():
    if not filename.endswith(".pdf"):
        continue

    # Match patterns like "3-5.pdf" or "3-5-1.pdf"
    sub_match = re.match(r"(\d+)-(\d+)", filename)
    prob_match = re.match(r"(\d+)-problems\.pdf", filename)

    if sub_match:
        major, minor = sub_match.groups()
        chapter_dir = os.path.join(".", major)
        subchapter_dir = os.path.join(chapter_dir, f"{major}.{minor}")

        os.makedirs(subchapter_dir, exist_ok=True)
        dest_path = os.path.join(subchapter_dir, filename)
        shutil.move(filename, dest_path)
        print(f"📂 Moved {filename} → {subchapter_dir}/")
        
        # Copy source.pdf from main directory into this subchapter folder
        main_source = "source.pdf"
        if os.path.exists(main_source):
            shutil.copy(main_source, os.path.join(subchapter_dir, "source.pdf"))
            print(f"📄 Copied source.pdf → {subchapter_dir}/")
        else:
            print("⚠️ source.pdf not found in main directory. Skipping copy.")

    elif prob_match:
        major = prob_match.group(1)
        chapter_dir = os.path.join(".", major)
        problems_dir = os.path.join(chapter_dir, "problems")

        os.makedirs(problems_dir, exist_ok=True)
        dest_path = os.path.join(problems_dir, filename)
        shutil.move(filename, dest_path)
        print(f"📂 Moved {filename} → {problems_dir}/")


##### Deleting Leftovers #####
base = Path.cwd()

# Remove 'pdf_chunks/' folder
pdf_chunks = base / "pdf_chunks"
if pdf_chunks.exists():
    print(f"🗑️ Removing folder: {pdf_chunks}")
    shutil.rmtree(pdf_chunks, ignore_errors=True)

# Remove 'chunk_*_artifacts/' folders
for folder in base.glob("chunk_*_artifacts"):
    if folder.is_dir():
        print(f"🗑️ Removing folder: {folder}")
        shutil.rmtree(folder, ignore_errors=True)

# Remove 'chunk_*.md' files
for file in base.glob("chunk_*.md"):
    if file.is_file():
        print(f"🗑️ Removing file: {file}")
        file.unlink()