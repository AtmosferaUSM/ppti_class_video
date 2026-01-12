######### Packages ##################
import sys
import shutil
import os
import re
import base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import PictureItem
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
import google.generativeai as genai

######### Force-disable pin_memory globally ###########
try:
    import torch.utils.data
    original_DataLoader = torch.utils.data.DataLoader

    class PatchedDataLoader(original_DataLoader):
        def __init__(self, *args, **kwargs):
            kwargs['pin_memory'] = False
            super().__init__(*args, **kwargs)

    torch.utils.data.DataLoader = PatchedDataLoader
    print("✅ DataLoader patched to force pin_memory=False")
except ImportError:
    print("⚠️ torch not available — skipping pin_memory patch")


########## Set ikB. PNG image of filesize smaller than ikB kB will be filtered out and not saved. ##########
ikB = 2.55    ### ikb = 2.64 works for Serway v10.  This is the default.
#ikB = 4.9    ### ikb = 4.9 works for Resnick and Halliday.

########## API Key Auto-Selection #############
# Note: default choice is gemini 

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
try:
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
except NameError:    
    env_path = Path(os.getcwd()).parent.parent.parent / '.env'

if env_path.is_file():
    print(f"✅ 1 File exists: {env_path}")
else:
    env_path = '.env'
    print(f"✅ 2 File exists: {env_path}")
    
load_dotenv(dotenv_path=env_path)
api_key_dsk = os.getenv("DEEPSEEK_API_KEY")
api_key_oai = os.getenv("OPENAI_API_KEY")
api_key_gemini = os.getenv("GEMINI_API_KEY")

if api_key_gemini:
    model_choice = 'gemini'  # Default: gemini; options: 'openai'  or 'deepseek'    
    api_key = api_key_gemini   
    #model_name ="gemini-2.5-pro-preview-03-25"
    model_name ="gemini-2.5-pro"    
    # model_name ="gemini-2.5-flash-preview-04-17"
    # model_name ="gemini-1.5-pro"            
    genai.configure(api_key=api_key)    
    generative_model = genai.GenerativeModel(model_name)
    chat_session = generative_model.start_chat()
    slidesfile="slides_gemini.pdf"
    
    print(f"1. model_choice {model_choice}")    
    
elif api_key_oai:        
    model_choice='openai'  # Default: gemini; options: 'openai'  or 'deepseek'    
       
    model_name = "gpt-5-mini"  # Default for png abstraction. Works better than 4o-mini but a bit more expensive    
    api_key = api_key_oai 
    client = OpenAI(api_key = api_key)
    slidesfile="slides_oai.pdf"
    print(f"2. model_choice {model_choice}")    
elif api_key_dsk:        
    model_choice = 'deepseek'  # Default: gemini; options: 'openai'  or 'deepseek'    
    model_name = "deepseek-reasoner" 
    #model_name = 'deepseek-chat'    
    api_key = api_key_dsk
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    slidesfile="slides_dsk.pdf"
    print(f"3. model_choice {model_choice}")

    
    

######### Forcefully use openai ######### 
model_choice='openai'  # Default: gemini; options: 'openai'  or 'deepseek'      
model_name = "gpt-5-mini"  # Default for png abstraction. Works better than 4o-mini but a bit more expensive    
api_key = api_key_oai 
client = OpenAI(api_key = api_key_oai)
slidesfile="slides_oai.pdf"
print(f"2. model_choice {model_choice}")    


input_doc_path = Path("source.pdf")
pages_root = Path("pages")
pages_root.mkdir(exist_ok=True)

def encode_image_b64(path):
    with open(path, "rb") as f:
        try:
            return base64.b64encode(f.read()).decode("utf-8")
        except:
            pass


######## Caption Extraction Prompt ########
prompt = """
Please examine the following textbook page image and extract all figure captions.

Guidelines:
1. Only extract captions that actually appear in the image — do not invent or hallucinate any figure numbers or labels.
2. Not all images on the page are formally captioned. If an image lacks a label like "Figure XX", do not assign one.
3. Use visual layout reasoning to associate text blocks with figures.
4. Format output like:
   - "Figure 21-3": Caption text here...
   - "Fig. TP21.9": Description of technical figure...
   - "Unlabeled image": Description of image content...
"""

####### Convert source.pdf into page PNGs and page PDFs ##########
pdf_pages = convert_from_path(str(input_doc_path), dpi=200)
reader = PdfReader(str(input_doc_path))

for i, (page_image, pdf_page) in enumerate(zip(pdf_pages, reader.pages), start=1):
    page_dir = pages_root / f"page_{i}"
    page_dir.mkdir(exist_ok=True)

    # Save PNG and PDF
    png_path = page_dir / f"page_{i}.png"
    page_image.save(png_path, "PNG")

    pdf_path = page_dir / f"page_{i}.pdf"
    writer = PdfWriter()
    writer.add_page(pdf_page)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Step 1: Extract figures with docling
    print(f"\n🖼️ Extracting figures from {pdf_path.name}...")
    pipeline_options = PdfPipelineOptions(
        images_scale=1.5,
        generate_page_images=False,
        generate_picture_images=True
    )
    doc_converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    try:
        conv_res = doc_converter.convert(pdf_path)
        doc = conv_res.document
        fig_counter = 0

        for item, _ in doc.iterate_items():
            if isinstance(item, PictureItem):
                fig_counter += 1
                fig_path = page_dir / f"fig_{fig_counter}.png"
                item.get_image(doc).save(fig_path, "PNG")

                if fig_path.stat().st_size < ikB * 1024:
                    fig_path.unlink()
                    print(f"🗑️ Removed small figure: {fig_path.name}")
                else:
                    print(f"✅ Saved: {fig_path.name}")

    except Exception as e:
        print(f"❌ Error extracting figures from {pdf_path.name}: {e}")
        continue

    # Step 2: Extract captions with GPT-4o
    print(f"📤 Submitting {png_path.name} to {model_choice} for caption extraction...")
    image_b64 = encode_image_b64(png_path)

    visual_prompt = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }
    ]

    try:
        if model_choice == 'gemini':
            response = chat_session.send_message(visual_prompt)
        else:
            response = client.chat.completions.create(
                model = model_name,
                messages=visual_prompt
            )
            
        result_text = response.choices[0].message.content.strip()
        #print('result_text ',result_text)
        caption_file = page_dir / f"page_{i}_captions.txt"
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"📝 Captions saved to: {caption_file.name}")
    except Exception as e:
        print(f"❌ Error processing {png_path.name}: {e}")
        

print(' begin mapped.txt')
# Constants
BATCH_SIZE = 4
pages_root = Path("pages")
page_dirs = sorted(pages_root.glob("page_*"))

summary = []

for page_dir in page_dirs:
    print(f"\n📘 Processing {page_dir.name}")

    caption_file = page_dir / f"{page_dir.name}_captions.txt"
    full_page_image = page_dir / f"{page_dir.name}.png"
    output_file = page_dir / "mapped.txt"

    if not caption_file.exists() or not list(page_dir.glob("fig_*.png")) or not full_page_image.exists():
        print("⚠️  Skipping: Missing required inputs (captions, page scan, or figures)")
        continue

    with open(caption_file, "r", encoding="utf-8") as f:
        caption_text = f.read().strip()

    if "no figure captions" in caption_text.lower():
        print("ℹ️  No captions found — skipping mapping.")
        with open(output_file, "w") as f:
            f.write("No captions present on this page.\n")
        continue

    fig_files = sorted(page_dir.glob("fig_*.png"), key=lambda x: int(re.findall(r'\d+', x.stem)[0]))
    mappings = []

    page_image_b64 = encode_image_b64(full_page_image)

    for i in range(0, len(fig_files), BATCH_SIZE):
        batch = fig_files[i:i + BATCH_SIZE]
        print(f"📤 Submitting batch {i//BATCH_SIZE + 1} with figures: {[f.name for f in batch]}")
        
        batch_filenames = "\n".join([f"- {fig.name}" for fig in batch])

        # Build prompt and messages
        prompt = f"""
You are shown several extracted figure images (e.g., fig_5.png, fig_21.png) from a textbook page.

You are also provided:
- A full-page scan of the same textbook page (source.png).
- A list of caption texts from the page (extracted textually).

Your task:
1. **Visually inspect** each figure and the full-page image.
2. **Infer the most appropriate figure caption** for each figure.
    - You may use clues from the layout, nearby text in the full-page image, or from the caption list.
    - If the figure includes its own visible caption, prioritize it.
    - Otherwise, infer the match using position and context.
3. Output for each figure:
    - The original filename (e.g., fig_1.png)
    - The inferred caption label (e.g., "Figure 21-5", "Fig. TP21.789", "Fig. TP41-4", "Figure 3-8a", "Figure 3-8b")
    - A standardized relabel filename: "Figure_X.png", where X is the caption label cleaned (spaces → underscores, punctuation removed) and includes any sub-label (a/b/c) if visible.

4. Only use the following figure filenames in your response — these are the actual figure images submitted in this batch:
    {batch_filenames}

    - Do not invent or refer to any filenames not listed above.
    - Do not guess or fabricate filenames like fig_5.png if it was not included.
    - Only assign captions to the provided filenames, and ignore any others.

Only return mappings for the given files. Format your response like:
fig_2.png : "Figure 21-5" : Figure_21-5.png
fig_1.png : "Fig. 41.3"   : Figure_41-3.png
fig_5.png : "Figure TP41.3"   : Figure_TP41-3.png
"""  
        messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_b64}"}},
            {"type": "text", "text": f"Figure captions:\n{caption_text.strip()}"},
        ] + [
            item
            for fig in batch
            for item in [
                {"type": "text", "text": f"Image: {fig.name}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image_b64(fig)}"}}
            ]
        ]
    }
]

        try:
            if model_choice == 'gemini':
                response = chat_session.send_message(messages)
            else:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages
                    )
            
            response_text = response.choices[0].message.content.strip()
            #print('response_text',response_text)
            for line in response_text.splitlines():
                if line.strip().startswith("fig_"):
                    try:
                        parts = line.strip().split(":", 2)
                        #if len(parts) >= 2:
                        #    mappings.append(f"{parts[0].strip()} : {parts[1].strip()}")
                        mappings.append(f"{parts[0].strip()} : {parts[1].strip()} : {parts[2].strip()}")
                        ##
                        filename1 = parts[0].strip()  # e.g., 'fig_3.png'
                        filename2 = parts[2].strip()  # e.g., 'Figure_213.png'
                        
                        # 🧩 Ensure sub-panel suffix (a/b/c) is preserved if present in caption
                        match_suffix = re.search(r"([a-z])(?=\.png$)", filename2)
                        if not match_suffix:
                            # Try to infer from text label, e.g., "Figure 3-8a"
                            m = re.search(r"[AaBbCcDdEeFf]", parts[1])
                            if m:
                                base, ext = os.path.splitext(filename2)
                                filename2 = f"{base}{m.group(0).lower()}{ext}"
        
                        source_path = page_dir / filename1
                        #destination_path = pages_root / filename2
                        destination_path = page_dir / filename2  # resolves to ../../
                        
                        if source_path.exists():
                            shutil.copy2(source_path, destination_path)
                            print(f"✅ Copied and renamed: {source_path} → {destination_path}") # ✅ Also copy to the global 'pages' folder for gen_slides access
                            #global_path = pages_root / filename2
                            #shutil.copy2(destination_path, global_path)
                            #print(f"📄 Duplicated: {destination_path} → {global_path}")
                        else:
                            print(f"❌ File not found: {source_path}")                      
                        ##
                    except:
                        pass
            print("✅ Batch processed successfully.")

        except Exception as e:
            err_msg = f"❌ Error: {e}"
            print(err_msg)
            mappings.append(err_msg)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(mappings))
    print(f"📝 Mappings saved to: {output_file}")
    summary.append({"Page": page_dir.name, "Mapped File": output_file.name})
    
    # Combine multipanel figures for this specific page (a, b, c subparts)
    # 🧩 --- Step 1: Merge true multipanel figures (a–f) ---
    from PIL import Image
    from collections import defaultdict

    def merge_subfigures(page_dir):
        print(f"\n🔧 Checking for multipanel figures to merge in {page_dir}...")
        figure_groups = defaultdict(list)

        # Find figure files with sublabels (a–f)
        for f in Path(page_dir).glob("Figure_*[a-f].png"):
            root = re.sub(r"[a-f](?=\.png$)", "", f.name)
            figure_groups[root].append(f)

        for root, files in figure_groups.items():
            files = sorted(files)
            if len(files) < 2:
                continue  # skip single-letter cases

            print(f"🧩 Merging {len(files)} subpanels for {root} → {[f.name for f in files]}")
            images = [Image.open(f) for f in files]

            # Determine layout
            w, h = images[0].size
            layout = "horizontal" if w >= h else "vertical"

            if layout == "horizontal":
                total_width = sum(img.width for img in images)
                max_height = max(img.height for img in images)
                merged = Image.new("RGB", (total_width, max_height), (255, 255, 255))
                x_offset = 0
                for img in images:
                    merged.paste(img, (x_offset, 0))
                    x_offset += img.width
            else:
                max_width = max(img.width for img in images)
                total_height = sum(img.height for img in images)
                merged = Image.new("RGB", (max_width, total_height), (255, 255, 255))
                y_offset = 0
                for img in images:
                    merged.paste(img, (0, y_offset))
                    y_offset += img.height

            merged_path = Path(page_dir) / root
            merged.save(merged_path)
            print(f"✅ Saved combined figure: {merged_path}")

            # Optionally delete originals after merging
            for f in files:
                try:
                    f.unlink()
                    print(f"🗑️ Deleted subpanel: {f.name}")
                except Exception as e:
                    print(f"⚠️ Could not delete {f.name}: {e}")

    merge_subfigures(page_dir)

    # 🧹 --- Step 2: Clean up stray 'f' suffixes *after* merge ---
    for f in Path(page_dir).glob("Figure_*f.png"):
        base = re.sub(r"f(?=\.png$)", "", f.name)
        # Only rename if it’s a single 'f' without other siblings a–e
        has_siblings = any(Path(page_dir).glob(f"{base}[a-e].png"))
        if not has_siblings:
            new_path = f.with_name(base)
            f.rename(new_path)
            print(f"🧹 Renamed stray f-suffix: {f.name} → {new_path.name}")
    
    

