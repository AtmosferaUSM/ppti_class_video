import google.generativeai as genai
from openai import OpenAI
import os
from pathlib import Path
import PyPDF2
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain.document_loaders import PyPDFLoader
#from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from langchain.vectorstores import FAISS
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from google.api_core.exceptions import ResourceExhausted
from langchain_core.exceptions import LangChainException
from langchain_core.exceptions import OutputParserException
import time

##### apikey auto-selection ######
##### default choice is gemini ######
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
# Load environment variables
try:
    #env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / '.env'  #### adjust the path to the credential relative to this file
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
    model_choice='gemini'  ### dafault: gemini; options: 'openai'  or 'deepseek'    
    api_key = api_key_gemini   
    model_name ="gemini-2.5-pro"
    # model_name ="gemini-2.0-flash"    
    # model_name ="gemini-2.5-flash-preview-04-17"
    # model_name ="gemini-1.5-pro"            
    genai.configure(api_key=api_key)    
    generative_model = genai.GenerativeModel(model_name)
    chat_session = generative_model.start_chat()
    slidesfile="slides_gemini.pdf"
    
    print(f"1. model_choice {model_choice}")    
    
elif api_key_oai:        
    model_choice='openai'  ### dafault: gemini; options: 'openai'  or 'deepseek'    
    #model_name = 'gpt-4o-mini-2024-07-18'    # Cheapest, but less effective than gpt-4o   
    model_name = "gpt-5-mini"                     # default for png abstraction. Works better than 4o-mini but a bit more expensive    
    api_key = api_key_oai 
    client = OpenAI(api_key = api_key)
    slidesfile="slides_oai.pdf"
    print(f"2. model_choice {model_choice}")    
elif api_key_dsk:        
    model_choice = 'deepseek'  ### dafault: gemini; options: 'openai'  or 'deepseek'    
    model_name = "deepseek-reasoner" 
    #model_name = 'deepseek-chat'    
    api_key = api_key_dsk
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    slidesfile="slides_dsk.pdf"
    print(f"3. model_choice {model_choice}")
##### end of apikey auto-selection ######

textbookfile="source.pdf"
scriptfile="script.txt"


# Extract text from PDF
def extract_text_from_pdf(pdf_file_path):
    text = ""
    with open(pdf_file_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def should_skip_narration(slide):
    title = slide.get("title", "").strip().lower()
    text_content = slide.get("text_content", "").strip().lower()

    skip_markers = [
        "ai-assisted lecture production",
        "artificial intelligence tools",
        "generation of presentation slides and narration scripts",
        "reviewed and approved by the instructor",
    ]

    combined_text = f"{title}\n{text_content}"

    return any(marker in combined_text for marker in skip_markers)

# Extract slide content from PDF
def extract_slide_contents(presentation_file_path):
    slide_contents = []
    with open(presentation_file_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                lines = page_text.strip().split('\n')
                title = lines[0].strip() if lines else ""
                content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
                slide_contents.append({"slide_number": i + 1, "title": title, "text_content": content})
            else:
                slide_contents.append({"slide_number": i + 1, "title": "", "text_content": ""})
    return slide_contents


# Estimate reading time
def estimate_reading_time(narration_script):
    words_per_minute = 143
    word_count = len(narration_script.split())
    minutes = word_count / words_per_minute
    minutes_int = int(minutes)
    seconds_int = int(round((minutes - minutes_int) * 60))
    return f"{minutes_int} min {seconds_int} sec"

# Improved generate_lecture_narration function with error handling
#def generate_lecture_narration(slide_content_list, textbook_content, slide_index, model_type='openai', retries=3, delay=10, model_name):
def generate_lecture_narration(slide_content_list, textbook_content, slide_index, model_choice, model_name, retries=3, delay=10):
 
    current_slide_content = slide_content_list[slide_index].get("text_content", "No Content")

    # Embeddings and Vector Store
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_text(textbook_content)
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    db = FAISS.from_texts(texts, embeddings)
    retriever = db.as_retriever()
    
    prompt_file = "gen_script_prompt.txt"
    #prompt_file = "gen_script_prompt_thesis.txt"

    # Load prompt from external file
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    
    
    # Model selection
    if model_choice == 'openai':
        llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), model_name = model_name, temperature=0.7)        
    elif model_choice == 'deepseek':
        llm = ChatOpenAI(openai_api_key=os.getenv("DEEPSEEK_API_KEY"), model_name  = model_name, temperature=0.7, base_url="https://api.deepseek.com")
    elif model_choice == 'gemini':        
        llm = ChatGoogleGenerativeAI(google_api_key=os.getenv("GEMINI_API_KEY"),  model = model_name, temperature=0.7)        
    else:
        raise ValueError("Unsupported model type")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=False,
        input_key="question"
    )

    attempt = 0
    while attempt <= retries:
        try:
            result = qa_chain.invoke({"question": current_slide_content})
            narration_script = result["result"].strip().strip('*').strip()
            return narration_script
        except (ResourceExhausted, LangChainException, OutputParserException) as e:
            #delay = delay + 1
            #print(f"Warning: Error encountered for slide {slide_index + 1}: {e}. Retrying in {delay} seconds...")
            print(f"Warning: Error encountered for slide {slide_index + 1}. Retrying in {delay} seconds...")
            attempt += 1
            time.sleep(delay)
    raise RuntimeError(f"Failed to generate narration after {retries} attempts for slide {slide_index + 1}.")
    print(' ')

# begin main here ###
#def generate_narration_scripts(slidesfile, textbookfile, scriptfile, model_choice='gemini'):
slide_contents = extract_slide_contents(slidesfile)
textbook_content = extract_text_from_pdf(textbookfile)

# Check if script.txt exists and rename it
if os.path.exists(scriptfile):
    count = 0
    while True:
        backup_name = f"script_{count+1}.txt"
        if not os.path.exists(backup_name):
            os.rename(scriptfile, backup_name)
            print(f"Existing {scriptfile} renamed to {backup_name}")
            break
        count += 1

with open(scriptfile, "w") as outfile:
    for i in range(len(slide_contents)):
        slide = slide_contents[i]
        ##
        if i == 0:
            title = slide_contents[0]['text_content'].strip()

            # --- normalize academic titles for TTS ---
            title = title.replace("Assoc. Prof.", "associate professor")
            title = title.replace("Assoc Prof.", "associate professor")
            title = title.replace("Prof.", "professor")
            title = title.replace("Prof ", "professor ")
            title = title.replace("Dr.", "doctor")
            title = title.replace("Dr ", "doctor ")

            outfile.write(
                "**Slide 1 [1 sec]:\n"
                "<break time=\"3s\" /> "
                f"{title} "
                "<break time=\"1s\" />**\n\n"
            )
            print("Written normalized narrated opening for Slide 1")
            continue  # Skip narration generation for the first slide
        
        if should_skip_narration(slide):
            print(f"Skipping narration for Slide {i+1} ({slide.get('title', '').strip()})")
            continue
        ##
        try:
            #narration = generate_lecture_narration(slide_contents, textbook_content, i, model_type=model_choice)
            retries=3; delay=10
            narration = generate_lecture_narration(slide_contents,     textbook_content, i, model_choice, model_name,retries, delay)
            #generate_lecture_narration(slide_content_list, textbook_content, slide_index, model_choice, model_name, retries=3, delay=10):
            
            estimated_time = estimate_reading_time(narration)
            formatted_narration = f"**Slide {i+1} [{estimated_time}]: \n{narration}**"
            outfile.write(formatted_narration + "\n\n")
            print(f"Generated narration for Slide {i+1}")
        except RuntimeError as e:
            print(e)
            outfile.write(f"**Slide {i+1}: Failed to generate narration after multiple attempts.\n\n")

print(f"Narration scripts saved to: {scriptfile}")

import fix_script_v26
