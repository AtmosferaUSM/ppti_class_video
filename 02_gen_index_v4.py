
######### Packages ##################
import os, torch
import re
import json
import PyPDF2
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
import sys
import logging
import time
import pymupdf  # PyMuPDF
import shutil
from multiprocessing import get_context
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import ImageRefMode
from llama_parse import LlamaParse


######### Text Encoding ##################
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

    
######### Model Choice ###################
try:
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
except NameError:
    env_path = Path(os.getcwd()).parent.parent.parent / '.env'
if not env_path.is_file():
    env_path = '.env'
load_dotenv(dotenv_path=env_path)

api_key_dsk = os.getenv("DEEPSEEK_API_KEY")
api_key_oai = os.getenv("OPENAI_API_KEY")
api_key_gemini = os.getenv("GEMINI_API_KEY")

if api_key_gemini:
    model_choice = 'gemini'
    api_key = api_key_gemini
    model_name = "gemini-2.5-pro-preview-03-25"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    chat_session = model.start_chat()
elif api_key_oai:
    model_choice = 'openai'
    model_name = "gpt-5"
    api_key = api_key_oai
    client = OpenAI(api_key=api_key)
elif api_key_dsk:
    model_choice = 'deepseek'
    model_name = "deepseek-reasoner"
    api_key = api_key_dsk
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
else:
    raise EnvironmentError("❌ No valid API key found in .env.")

model_choice = 'openai'
model_name = 'gpt-5'
api_key = api_key_oai
client = OpenAI(api_key=api_key_oai)

slidesfile = "slides_oai.pdf"
print(f"Forcefully use model_choice = {model_choice}")
print(f'{model_choice, model_name}')

def extract_pages(pdf_path, start_page, end_page, output_filename):
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_writer = PyPDF2.PdfWriter()
            for page_num in range(start_page - 1, end_page):
                try:
                    page = pdf_reader.pages[page_num]
                    pdf_writer.add_page(page)
                except IndexError:
                    print(f"Warning: Page {page_num + 1} out of range. Skipping.")
            with open(output_filename, 'wb') as output_file:
                pdf_writer.write(output_file)
        print(f"Pages {start_page}-{end_page} extracted successfully to {output_filename}")
    except FileNotFoundError:
        print(f"Error: File not found: {pdf_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def split_pdf_into_chunks(pdf_path, output_dir, n_chunks):
    """
    Split contents of PDF into chunks.
    """
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    total_pages = doc.page_count
    pages_per_chunk = (total_pages + n_chunks - 1) // n_chunks
    chunk_paths = []
    for i in range(n_chunks):
        start_page = i * pages_per_chunk
        end_page = min(start_page + pages_per_chunk, total_pages)
        if start_page >= end_page:
            break
        chunk_path = output_dir / f"chunk_{i+1}.pdf"
        chunk_doc = pymupdf.open()
        for page_num in range(start_page, end_page):
            chunk_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        chunk_doc.save(chunk_path)
        chunk_paths.append(chunk_path)
    return chunk_paths

def convert_pdf_to_md(args):
    """
    Split contents of PDF into MD.
    """
    chunk_path, output_dir = args
    output_dir = Path(output_dir)
    chunk_index = chunk_path.stem.split('_')[-1]
    md_path = output_dir / f"chunk_{chunk_index}.md"
    options = PdfPipelineOptions(
        images_scale=1.0,
        generate_page_images=False,
        generate_picture_images=False,
        format_hints={"no_ocr": True, "no_tables": True, "no_figures": True},
    )
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    result = converter.convert(chunk_path)
    result.document.save_as_markdown(md_path, image_mode=ImageRefMode.REFERENCED)
    return md_path

def stitch_md_chunks(md_paths, output_path):
    """
    Stitch MD chunks.
    """
    with open(output_path, "w", encoding="utf-8") as outfile:
        for md_file in sorted(md_paths, key=lambda x: int(x.stem.split('_')[-1])):
            with open(md_file, "r", encoding="utf-8") as infile:
                outfile.write(infile.read() + "\n\n")

########## The Main Program #####################

if __name__ == "__main__":
    start_time = time.time()
    pdf_path = "source.pdf"
    
    start_page = 1     # Number of slides can be changed depending on the content.
    end_page = 20      # The length of the video would change based on the slides number. The prompt below, the number of slides, e.g., 20, would also needed to be changed.
    
    output_filename = f"{start_page}_{end_page}.md"
    
    # Converting the PDF to MD but it is used only for the table of contents.
    extract_pages(pdf_path, start_page, end_page, output_filename)

    INPUT_PDF = output_filename
    OUTPUT_DIR = Path(".")
    final_md = "source.md"

    if torch.cuda.is_available():
        print("CUDA is available! PyTorch can use your GPU.")
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        NUM_CHUNKS = 4

        CHUNK_DIR = Path("pdf_chunks")
        chunk_paths = split_pdf_into_chunks(INPUT_PDF, CHUNK_DIR, NUM_CHUNKS)

        ctx = get_context("spawn")
        with ctx.Pool(processes=NUM_CHUNKS) as pool:
            md_paths = pool.map(convert_pdf_to_md, [(path, OUTPUT_DIR) for path in chunk_paths])
        stitch_md_chunks(md_paths, final_md)

    else:
        print("CUDA is NOT available. Falling back to single-pass Markdown conversion...")
        options = PdfPipelineOptions(
            images_scale=1.0,
            generate_page_images=False,
            generate_picture_images=False,
            format_hints={"no_ocr": True, "no_tables": True, "no_figures": True},
        )
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        result = converter.convert(INPUT_PDF)
        result.document.save_as_markdown(final_md, image_mode=ImageRefMode.REFERENCED)

    logging.info(f"✅ Done. {output_filename} has been converted to: {final_md}")
    logging.info(f"⏱️ Total time: {time.time() - start_time:.2f} seconds.")

    reader = PdfReader(pdf_path) # Use the source.pdf in the main folder.
    # Extract all text from the PDF
    pdf_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pdf_text += f"\n\n--- PAGE {i+1} ---\n{text}"

    if not pdf_text.strip():
        raise RuntimeError("❌ PDF text could not be extracted.")

    # --- Extract TOC-like preview (first 50 pages or fewer) ---
    toc_text = ""
    for i in range(min(50, len(reader.pages))):
        page_text = reader.pages[i].extract_text()
        if page_text:
            toc_text += page_text + "\n"

    if not toc_text.strip():
        raise RuntimeError("❌ TOC text could not be extracted.")


    # Read PDF table of contents only if available.
    
    
    toc_text = ""
    for i in range(min(50, len(reader.pages))):
        page = reader.pages[i].extract_text()
        if page:
            toc_text += page + "\n"
    if not toc_text.strip():
        raise RuntimeError("❌ TOC text could not be extracted.")
    
    
    # Read markdown content for reference for the table of contents generation.
    markdown_path = "source.md"
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
    
    markdown_excerpt = markdown_text

    # Read the prompt content from external file
    prompt_file = "gen_index_prompt.txt"

        
    prompt_path = Path(__file__).resolve().parent / prompt_file
    with open(prompt_path, 'r', encoding='utf-8') as pf:
        prompt = pf.read()
    # Wrap prompt content and pdf_content
    prompt = prompt.replace("{markdown_excerpt}", markdown_excerpt)
    prompt = prompt.replace("{toc_text}", toc_text)
    prompt = prompt.replace("{pdf_text}", pdf_text)

    print(f"[INFO] Prompt loaded from {prompt_path}")
    
    # Query LLM
    if model_choice == 'gemini':
        response_text = chat_session.send_message(prompt).text
    elif model_choice in ['openai', 'deepseek']:
        response_text = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
    else:
        raise ValueError("Invalid model.")
    
    print("🔎 Raw LLM Response:\n", response_text)
    
    # Strip markdown fences
    response_text = response_text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    if not response_text:
        raise RuntimeError("❌ Empty response from LLM.")
    
    # Parse JSON output
    try:
        result = json.loads(response_text)
    except Exception as e:
        raise RuntimeError("❌ Failed to parse JSON from LLM.") from e
    
    # Save result
    with open("subchapter_index_physical.json", "w", encoding="utf-8") as f:
        json.dump(result["subchapters"], f, indent=2)
    
    print(f"✅ subchapter_index_physical.json created with offset {result['offset']}.")