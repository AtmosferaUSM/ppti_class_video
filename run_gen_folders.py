import subprocess, sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'


### specify the version of the constituent codes here ###
va = 3; fa = f'gen_index_v{va}.py'
vb = 0; fb = f'gen_folders_v{vb}.py'
### end of specify the version of the constituent codes here ###

# List of required python codes to be run in order (including source.pdf)
required_files = [fa, fb,'source.pdf']


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
    #cmd = ["python", script_file]
    cmd = ["python", "-u", script_file]
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'  # Explicitly set encoding to handle Unicode characters
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # Add a short pause to ensure file system I/O completes
        time.sleep(1)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running: {' '.join(cmd)}")
        print("Return code:", e.returncode)
        print("Output:", e.stdout)
        print("Error output:", e.stderr)
        sys.exit(1)  # Exit the entire process if any of the scripts fail
