######### Packages ##################
import shutil
import fix_latex_27
import subprocess, os, sys
from pathlib import Path
from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader
import google.generativeai as genai
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
    
##### Load environment and auto selection of llm based on whether the API key of the LLMs are inside .env. #####
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

##### Select Model #######
if api_key_gemini:
    model_choice='gemini'
    api_key, model_name = api_key_gemini, "gemini-2.5-pro"
    genai.configure(api_key=api_key)
    generative_model = genai.GenerativeModel(model_name)
    chat_session = generative_model.start_chat()
elif api_key_oai:
    model_choice='openai'
    api_key, model_name = api_key_oai, "gpt-5-mini"
    client = OpenAI(api_key=api_key)
elif api_key_dsk:
    model_choice='deepseek'
    api_key, model_name = api_key_dsk, "deepseek-reasoner"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
else:
    raise RuntimeError("No API key found for Gemini, OpenAI, or Deepseek")
# end of Load environment and auto selection of llm based on whether the API key of the LLMs are inside .env. 

def append_ai_disclaimer_slide(latex_text):
    disclaimer_frame = r"""
% AI_DISCLOSURE_SLIDE
\begin{frame}{AI-Assisted Lecture Production}
\small
This lecture video was produced with the assistance of artificial intelligence tools.

\vspace{0.5em}

The academic content, source materials, and instructional design were prepared and curated by the instructor.

\vspace{0.5em}

Artificial intelligence was used only to assist in the generation of presentation slides and narration scripts. The final material was reviewed and approved by the instructor.

\vfill
\centering
\footnotesize School of Industrial Technology\\
Universiti Sains Malaysia
\end{frame}
"""
    end_doc = r"\end{document}"
    if end_doc in latex_text:
        return latex_text.replace(end_doc, disclaimer_frame + "\n" + end_doc, 1)
    return latex_text + "\n" + disclaimer_frame

def gen_slide(llmmodel, model_name):
    print(f"[INFO] Configuring LLM client for model: {llmmodel}")

    if llmmodel == 'gemini':
        client = genai.GenerativeModel(model_name)
    elif llmmodel == 'openai':
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    elif llmmodel == 'deepseek':
        client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    else:
        raise ValueError("Unsupported LLM model")

    def load_pdf(fp):
        print(f"[INFO] Loading PDF: {fp}")
        loader = PyPDFLoader(fp)
        pages = loader.load_and_split()
        content = "\n".join(p.page_content for p in pages)
        print(f"[INFO] Loaded {len(pages)} pages, {len(content)} chars.")
        return content

    pdf_content = load_pdf('source.pdf')

    # Read the prompt content from external file
    prompt_file = "gen_slides_prompt.txt"
    
    
    prompt_path = Path(__file__).resolve().parent / prompt_file
    with open(prompt_path, 'r', encoding='utf-8') as pf:
        prompt = pf.read()
    # Wrap prompt content and pdf_content
    prompt = prompt.replace("{pdf_content}", pdf_content)

    print(f"[INFO] Prompt loaded from {prompt_path}")

    if llmmodel in ('openai', 'deepseek'):
        print(f"[INFO] Sending prompt to {llmmodel}")
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role":"system","content":"You are an AI assistant that generates high-quality LaTeX Beamer slides for class presentations."},
                {"role":"user","content":prompt}
            ],
            stream=False
        )
        latex_presentation = resp.choices[0].message.content
    else:  # gemini
        print("[INFO] Sending prompt to Gemini")
        resp = client.generate_content(prompt)
        latex_presentation = resp.text

    # Clean code fences
    lines = latex_presentation.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    latex_presentation = "\n".join(lines)
    
    # Append AI disclosure slide before saving/compiling
    latex_presentation = append_ai_disclaimer_slide(latex_presentation)

    out_base = {
        'openai':'slides_oai',
        'deepseek':'slides_dsk',
        'gemini':'slides_gemini'
    }[llmmodel]

    with open(out_base + '.tex','w',encoding='utf-8') as f:
        f.write(latex_presentation)

    ## Begin compiling latex after exiting the LLM phase ##
    tex_file = out_base + '.tex'
    pdf_file = out_base + '.pdf'
    try: #### 1
      result = subprocess.run(
        ['pdflatex', '-interaction=nonstopmode', tex_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True)
      if result.returncode == 0:
        print(f"✅ pdflatex compilation succeeded for '{tex_file}' at 1st attempt")      
    except subprocess.CalledProcessError:
      print(f"✅ pdflatex compilation failed for '{tex_file}' at 1st attempt")      
      fix_latex_27.clean_tex_file(tex_file)
      print(f'clean_tex_file({tex_file}) processed (1st round)') 
    ####        
      ###
      try: #### 2
        result = subprocess.run(
          ['pdflatex', '-interaction=nonstopmode', tex_file],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          check=True
          )
        if result.returncode == 0:
          print(f"✅ pdflatex compilation succeeded for '{tex_file}' at 2nd attempt")
      except subprocess.CalledProcessError:
        print(f"❌ pdflatex compilation failed for '{tex_file} at 2nd attemp.")
        #fix_latex_26.clean_tex_file2(tex_file,model_choice)
        fix_latex_27.clean_tex_file2(tex_file,model_choice,model_name,api_key)
        print(f'clean_tex_file2({tex_file,model_choice,model_name}) processed (2nd round)')             
      ###
        ###
        try: #### 3
          result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', tex_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
            )
          if result.returncode == 0:
            print(f"✅ pdflatex compilation succeeded for '{tex_file}' at 3rd attempt")
        except subprocess.CalledProcessError:
          print(f"✅ pdflatex compilation succeeded for '{tex_file}' at 3rd attempt")
          fix_latex_27.clean_tex_file(tex_file)
          print(f'clean_tex_file({tex_file}) processed (3rd round)') 
        ###
          ###
          try:  #### 4
            result = subprocess.run(
              ['pdflatex', '-interaction=nonstopmode', tex_file],
              stdout=subprocess.PIPE,
              stderr=subprocess.PIPE,
              check=True
              )
            if result.returncode == 0:
              print(f"✅ pdflatex compilation succeeded for '{tex_file}' at 4th attempt")
          except subprocess.CalledProcessError:
            print(f"✅ pdflatex compilation failed for '{tex_file}' at 4th attempt")             
          ###
        ###
    ## end of compiling latex after exiting the LLM phase ##    


### begin the main program here #######################################################
######### Copy all final Figure_*.png from each page folder to working directory #########
for page_dir in Path("pages").glob("page_*"):
    for fig in page_dir.glob("Figure_*.png"):
        shutil.copy2(fig, Path.cwd() / fig.name)
        print(f"📄 Copied {fig.name} → working directory for LaTeX")

print(f"[INFO] Starting slide generation process for model: {model_choice}")
gen_slide(model_choice,model_name)
print(f"[INFO] Completed slide generation process for model: {model_choice}")
print("[INFO] Cleaning up auxiliary files...")


aux_files = [  "slides_dsk", "slides_gemini", "slides_oai" ]
exts = [".log", ".nav", ".out", ".snm", ".toc", ".aux", ".synctex.gz"]
for base in aux_files:
    for ext in exts:
        try:
            os.remove(base + ext)
            print(f"[INFO] Removed auxiliary file: {base + ext}")
        except:
            pass


print("[INFO] Cleanup of auxiliary files complete.")