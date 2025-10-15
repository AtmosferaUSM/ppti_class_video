import subprocess, sys, os

filtered_files = [ 'run_gen_slides.py' , 'run_gen_video.py']

### Run each script in order
for script_file in filtered_files:
    cmd = ["python", script_file]
    if not script_file in [ ]:                         ### default, not filter any *.py out.
        try:        
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running: {' '.join(cmd)}")
            print("Return code:", e.returncode)
            print("Output:", e.output)
            print("Error output:", e.stderr)
            sys.exit(1)  # Exit the entire process if any of the scripts fails.
