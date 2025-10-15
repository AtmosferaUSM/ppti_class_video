import os
import re
from pathlib import Path
import shutil
#import os
import time
#from pathlib import Path
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain.chat_models import ChatOpenAI
#from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException
from langchain_core.exceptions import LangChainException

#retries = 3

def extract_math_segments(text):
    inline_math = re.findall(r'\$(.+?)\$', text)
    escaped_inline_math = re.findall(r'\\\((.+?)\\\)', text)
    display_math = re.findall(r'\\\[(.+?)\\\]', text)
    equations = re.findall(r'\\begin\{equation\}(.+?)\\end\{equation\}', text, re.DOTALL)
    return inline_math + escaped_inline_math + display_math + equations

def replace_ambiguous_braces_in_math_safe(text):
    def correct_math_segment(segment):
        corrected = []
        i = 0
        while i < len(segment):
            if segment[i] == '{':
                if i > 0 and segment[i-1] == '\\':
                    corrected.append('{')
                else:
                    corrected.append('<')
            elif segment[i] == '}':
                corrected.append('>')
            else:
                corrected.append(segment[i])
            i += 1
        return ''.join(corrected)

    def replacer(wrapper):
        def inner(m):
            inner_content = m.group(1)
            return wrapper(correct_math_segment(inner_content))
        return inner

    text = re.sub(r'\$(.+?)\$', replacer(lambda x: f"${x}$"), text)
    text = re.sub(r'\\\((.+?)\\\)', replacer(lambda x: f"\\({x}\\)"), text)
    text = re.sub(r'\\\[(.+?)\\\]', replacer(lambda x: f"\\[{x}\\]"), text)
    text = re.sub(r'\\begin\{equation\}(.+?)\\end\{equation\}', 
                  replacer(lambda x: f"\\begin{{equation}}{x}\\end{{equation}}"), 
                  text, flags=re.DOTALL)
    return text

def balance_braces_globally(text):
    stack = []
    corrected_text = []
    corrections = []
    for i, char in enumerate(text):
        corrected_text.append(char)
        if char == '{':
            stack.append(i)
        elif char == '}':
            if stack:
                stack.pop()
            else:
                corrected_text.pop()
                corrections.append(f"Unmatched closing brace at position {i}")
    if stack:
        for idx in stack:
            corrected_text.append('}')
            corrections.append(f"Missing closing brace for opening at position {idx}")
    return ''.join(corrected_text), corrections

def remove_non_latex_blocks(lines):
    cleaned_lines = []
    non_latex_flagged = False
    for line in lines:
        if re.match(r'^[-*]\s+', line.strip()) and not line.strip().startswith(r'\\item'):
            non_latex_flagged = True
            continue
        cleaned_lines.append(line)
    return cleaned_lines, non_latex_flagged

def process_latex_file_safe(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        original_text = f.read()

    lines = original_text.splitlines()
    cleaned_lines, non_latex_found = remove_non_latex_blocks(lines)
    text = '\n'.join(cleaned_lines)

    text = replace_ambiguous_braces_in_math_safe(text)
    text, brace_corrections = balance_braces_globally(text)

    corrections_made = non_latex_found or bool(brace_corrections)
    result_info = []

    if corrections_made:
        cleaned_path = Path(input_file).with_name(f"cleaned_{Path(input_file).name}")
        with open(cleaned_path, 'w', encoding='utf-8') as f:
            f.write(text)
        result_info.append(f"Corrections made. Saved to: {cleaned_path.name}")
        if non_latex_found:
            result_info.append("Removed non-LaTeX markdown-like blocks.")
        if brace_corrections:
            result_info.extend(brace_corrections)
    else:
        result_info.append("No targeted syntax errors were found or corrected.")

    return result_info


## begin block
def fix_missing_braces(content):
    stack = []
    corrected_content = []

    for char in content:
        corrected_content.append(char)
        if char == '{':
            stack.append('{')
        elif char == '}':
            if stack:
                stack.pop()

    # Add missing closing braces at the end if any
    missing_braces = len(stack)
    if missing_braces > 0:
        print(f"Fixing {missing_braces} missing closing curly brace(s)...")
        corrected_content.extend('}' * missing_braces)

    return ''.join(corrected_content)


def fix_end_frame_lines(content):
    lines = content.splitlines()
    fixed_lines = []

    for line in lines:
        if line.strip().startswith('\\end{frame') and not line.strip().endswith('}'):
            print(f"Fixing line: {line}")
            fixed_lines.append('\\end{frame}')
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def clean_tex_file(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        original_content = f.read()
    #print(' ' )
    print(f'Executing clean_tex_file({input_file})')
    
    # Check for markdown contamination
    markdown_pattern = re.compile(r'(\`{3}|^#+\s)', re.MULTILINE)
    markdown_contamination = bool(markdown_pattern.search(original_content))
    if markdown_contamination:
        print("Markdown contamination detected. Cleaning file...")
    else:
        print("No markdown contamination detected.")

    # Extract content between \documentclass and \end{document}
    docclass_pattern = re.compile(r'(\\documentclass.*?\\end\{document\})', re.DOTALL)
    match = docclass_pattern.search(original_content)

    if not match:
        raise ValueError("The file does not contain valid LaTeX document structure.")

    cleaned_content = match.group(1)

    # Remove markdown code blocks or triple backticks
    cleaned_content = re.sub(r'`{3}.*?`{3}', '', cleaned_content, flags=re.DOTALL)
    cleaned_content = cleaned_content.replace('```', '')

    # Fix erroneous '>' symbols that should be '}'
    #cleaned_content = cleaned_content.replace('>', '}')

    # Fix missing curly braces properly
    cleaned_content = fix_missing_braces(cleaned_content)

    # Fix specifically \end{frame lines
    cleaned_content = fix_end_frame_lines(cleaned_content)
    
     # === Comment out all instances of \pause ===
    #cleaned_content = re.sub(r'^(\\pause\s*)$', r'% \1', cleaned_content, flags=re.MULTILINE)
    #cleaned_content = re.sub(r'^\s*\\pause\s*$', r'% \pause', cleaned_content, flags=re.MULTILINE)
    cleaned_content = re.sub(r'^\s*\\pause\s*$', r'% \\pause', cleaned_content, flags=re.MULTILINE)


    # Write cleaned content to new file
    output_file = f'cleaned_{input_file}'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

    print(f"Cleaned file saved as: {output_file}")

    # Check if cleaning modified the original file significantly
    if original_content.strip() != cleaned_content.strip():
        defective_file = f'defective_{input_file}'
        try:
            os.remove(defective_file)
        except:
            pass
        os.rename(input_file, defective_file)
        print(f"{input_file} has been renamed to {defective_file}")
        
        shutil.copy(output_file, input_file)
        print(f"{output_file} has been copied to {input_file}")
        
        os.remove(output_file)
        print(f"{output_file} has been removed.")
        #print(f"Original file was defective and corrected. Original file renamed as: {defective_file}")
    else:
        print("Original file was not defective and required no corrections.")        
## end block


######
def clean_tex_file2(input_file,model_choice,model_name,api_key):
    #print(' ' )
    #print(f'Executing clean_tex_file2({input_file,model_choice,model_name})')
    # === Config ===
    slidesfile = input_file
    #model_choice = llm  
    retries = 3
    
    # === Prompt Template ===
    prompt_template = """
You are an expert LaTeX proofreader.
Your task is to scan through the following LaTeX slide content and identify math mode expressions that mistakenly use curly braces `{{` or `}}` instead of comparison operators `<` or `>`.

Specifically, correct these two types of errors:
1. Mistaken use of `{{` instead of `>`. For example, `$r {{ R$` should be `$r > R$`; `$C_1 }} C_2$` should be `$C_1 > C_2$`.
2. Mistaken use of `}}` instead of `>`. For example, `$r }} R$` should be `$r > R$`; `$C_2 {{ C_1$` should be `$C_2 < C_1$`.

Do not modify other valid uses of `{{` and `}}` such as in subscripts (e.g., `x_{{0}}` or `\vec{{E}}`).

You must perform a full LaTeX syntax validation. Line by line, check the content for any LaTeX grammar issues such as:
- Ensure that all mathematical expressions are properly enclosed in math mode delimiters. For instance, the expression A=(0.18m)^2 should be written as $A=(0.18\\mathrm{{m}})^2$ to correctly format it in math mode. This ensures that variables, numbers, and units are appropriately rendered.
- Ensure the '^' symbol does not appear in regular text. Always enclose expressions containing '^' in math mode. For example, instead of writing A=(0.18m)^2 in text, format it as $A=(0.18 \\mathrm{{m}})^2$ or \\[ A=(0.18 \\mathrm{{m}})^2 \\] to ensure proper mathematical rendering.
- Unmatched or unbalanced braces `{{}}`
- Improper math mode delimiters (e.g., unpaired `$` symbols)
- Other typical syntax errors that would cause `pdflatex` compilation to fail

Correct any such errors and return a LaTeX version that is fully syntactically valid and compilable.

Context: {context}
Slide Content: {question}
"""
    
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    print('model_choice:',model_choice)
    # === LLM Setup ===
    if model_choice == 'openai' or model_choice == 'chatgpt':
        llm = ChatOpenAI(openai_api_key = api_key, model_name = model_name, temperature=0.7)        
    elif model_choice == 'deepseek':
        llm = ChatOpenAI(openai_api_key = api_key, model_name = model_name, temperature=0.7,base_url="https://api.deepseek.com")                
    elif model_choice == 'gemini':
        
        llm = ChatGoogleGenerativeAI(google_api_key=api_key, model = model_name, temperature=0.7)        
    else:
        raise ValueError("Unsupported model type")
    
    # === Dummy retriever ===
    from langchain_core.retrievers import BaseRetriever
    
    class DummyRetriever(BaseRetriever):
        def _get_relevant_documents(self, query):
            return []
    
    retriever = DummyRetriever()
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=False,
        input_key="question"
    )
    
    # === Slide Processing Function ===
    def correct_latex_math_errors(slide_text: str, context: str = "LaTeX slide content"):
        attempt = 0
        delay = 2
        while attempt <= retries:
            try:
                result = qa_chain.invoke({"question": slide_text, "context": context})
                return result["result"].strip()
            except (LangChainException, OutputParserException) as e:
                print(f"Warning: Error encountered. Retrying in {delay} seconds...")
                attempt += 1
                time.sleep(delay)
        raise RuntimeError("Failed to correct LaTeX after multiple attempts.")
    
    # === Read and fix the LaTeX file ===
    with open(slidesfile, 'r', encoding='utf-8') as f:
        slide_text = f.read()
    
    print("Loaded LaTeX file. Characters:", len(slide_text))
    
    fixed_text = correct_latex_math_errors(slide_text)
    
    # Remove leading markdown like ```latex and trailing ```
    fixed_lines = fixed_text.splitlines()
    
    if fixed_lines[0].strip().startswith("```"):
        print("Removed markdown header from first line.")
        fixed_lines = fixed_lines[1:]
    
    if fixed_lines[-1].strip() == "```":
        print("Removed markdown footer from last line.")
        fixed_lines = fixed_lines[:-1]
    
    cleaned_text = "\n".join(fixed_lines)    
    if cleaned_text == slide_text:
        print("No corrections were made to the original file.")
    else:        
        #print("Corrections were made and applied to the output.")
        # Backup original file
        backup_file = "defective_" + slidesfile
        print("Corrections were made to {slidesfile}")
        try:
            os.rename(slidesfile, backup_file)
            print("The input file {slidesfile} is backed up as:", backup_file)
        except:
            print("The input file {slidesfile} is not backed up ")
    
        # Overwrite original file with cleaned version
        dfile='temp.tex'
        #with open(slidesfile, 'w', encoding='utf-8') as f:
        with open(dfile, 'w', encoding='utf-8') as f:
            print(f'Writting corrected Latex file to {dfile}')
            f.write(cleaned_text)
            #print(cleaned_text)
        
        try:            
            shutil.copyfile(dfile, slidesfile)    
            print(f'Corrected Latex file {dfile} is copied to {slidesfile}')
            os.remove(dfile)
            print(f'{dfile} is removed')
        except:
            print(f'Corrected Latex file {dfile} is NOT copied to {slidesfile}')
        #print("Corrected LaTeX saved to original filename:", slidesfile)        

### comment out the followng by default ####
#llm = 'gemini'
#input_file='slides_gemini.tex'
#fix_latex(input_file,llm)
