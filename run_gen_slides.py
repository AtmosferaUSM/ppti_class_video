import subprocess, sys, os

### specify the version of the constituent codes here ###
#va = 64; fa = f'abs_figures_source_v{va}.py'
va = 14; fa = f'abs_figures_merged_v{va}.py'
vb = 14; fb = f'gen_slides_v{vb}.py'
### end of specify the version of the constituent codes here ###

# List of required python codes to be run in order (including source.pdf)
required_files = [fa, fb,'source.pdf']
#required_files = [fb,'source.pdf']

### Checking if all files are present
missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    print("Error: The following required files are missing:")
    for f in missing_files:
        print(f" - {f}")
    sys.exit(1)
else:
    print(f'All required files are present: {required_files}\n')

### Create a filtered list (excluding 'source.pdf')
filtered_files = [f for f in required_files if f != "source.pdf"]

### Run each script in order
for script_file in filtered_files:
    cmd = ["python", script_file]
    #if not script_file in [ fb, fc, fd, fe, ff ]:     ### for TS
    #if not script_file in [ fa ]:                     ### for TS
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
