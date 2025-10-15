import os, subprocess, sys, shutil
from pathlib import Path
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure UTF-8 encoding for stdout (useful for Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')


def run_cmd(root, script_file, source_path):
    root = os.path.abspath(root)
    script_path = os.path.join(root, script_file)
    cmd = ["python", script_path]

    result = None
    orig_dir = os.getcwd()

    try:
        copyfiles(source_path, root)
        os.chdir(root)
        print(f'Running {cmd} in: {os.getcwd()}')

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Subprocess failed: {' '.join(cmd)}")
            print("Return code:", e.returncode)
            print("Output:", e.output)
            print("Error output:", e.stderr)
        except Exception as e:
            print(f"❌ Unexpected error while running subprocess: {e}")

    except Exception as e:
        print(f"❌ Failed during setup or file handling: {e}")

    finally:
        os.chdir(orig_dir)
        print(f'Finished running {cmd}')

        if result:
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
        print('')

        

def copyfiles(source_path, des_path):
    for f in os.listdir(source_path):
        if f != 'source.pdf':
            full_path = os.path.join(source_path, f)
            dest_path = os.path.join(des_path, f)

            if os.path.isfile(full_path):
                # Skip if source and destination are the same file
                if os.path.abspath(full_path) == os.path.abspath(dest_path):
                    continue

                try:
                    shutil.copy2(full_path, des_path)
                except Exception as e:
                    print(f"Error copying {full_path} to {des_path}: {e}")
            

def check_files_recursively(base_directory,source_path):
    """
    Recursively scans all subdirectories within the base_directory.
    For each subdirectory that contains 'source.pdf':
        - If the subdirectory is named 'problems':
            - Checks if it contains any files ending with '.xml' and '.tex'.
            - Prints the full path of the subdirectory along with an informative message.
        - Else:
            - Checks if 'script.txt' exists.
            - Prints the full path of the subdirectory along with an informative message.
    Skips any directories named 'mine', 'test', or 'problems_oai' etc as listed in excluded_dirs.
    """
    required_files = {"script.txt"}
    excluded_dirs = {"mine", "test", "problems_oai","storage","problems_DeepSeek","temp","previous_attempts"}

    for root, dirs, files in os.walk(base_directory, topdown=True):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        # Check if 'source.pdf' exists in the current directory
        if "source.pdf" not in files:
            continue  # Skip this directory

        # Handle 'problems' subdirectory as a special case
        if os.path.basename(root) == "problems":
            has_xml = any(file.endswith(".xml") for file in files)
            has_tex = any(file.endswith(".tex") for file in files)
            if has_tex and not has_xml:                
                print(f"✅ 'problems' directory with 'source.pdf' found at: {os.path.abspath(root)}")
                print("Contains only '.tex' but not '.xml' files.")
                script_file = 'run_gen_xml.py'
                
                run_cmd(root,script_file,source_path)
                
            elif has_xml and not has_tex:                                        
                print(f"✅ 'problems' directory with 'source.pdf' found at: {os.path.abspath(root)}")
                print( "Contains only '.xml' but not '.tex' files.")
                script_file = 'run_gen_problems.py'
                
                run_cmd(root,script_file,source_path)
                
                
            elif not has_tex and not has_xml:
                print(f"✅ 'problems' directory with 'source.pdf' found at: {os.path.abspath(root)}")
                print("Missing both '.xml' and '.tex' files.")
                script_file = 'run_gen_problems.py'
                run_cmd(root,script_file,source_path)
                
        # For other directories, check for 'script.txt'
        present_files = set(files)
        missing_files = required_files - present_files

        if not missing_files:
            print(f"✅ Required file(s) {required_files} exist in: {os.path.abspath(root)}\n")
        else:
            print('root:',root)
            last_part = os.path.basename(root)
            
            # 🚫 Skip if we're still in the base directory
            if os.path.abspath(root) == os.path.abspath(base_directory):
                print(f"⚠️ Skipping script execution in base directory: {root}")
                continue
                        
            if not last_part == 'problems':
                print(f"Missing file(s) {required_files} in: {os.path.abspath(root)}")
                script_file = 'run_gen_slides_videos.py'
                run_cmd(root,script_file,source_path)
            print('')

template_dir = Path(".")
#"llm_template"

#if os.path.isdir(template_dir):
#    print(f"Directory {template_dir} found.")
base_dir = "."
check_files_recursively(base_dir,template_dir)

