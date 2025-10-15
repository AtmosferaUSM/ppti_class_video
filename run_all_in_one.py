import subprocess, sys, os, time
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'

### Specify the version of the constituent codes here ###
va = 1; fa = f'run_gen_folders.py'
vb = 0; fb = f'run_all_dirs.py'
### End of version block ###

required_files = [fa, fb, 'source.pdf']
filtered_files = [f for f in required_files if f != "source.pdf"]

# Set up log file
log_filename = "run_all.log"
log_file = open(log_filename, "a", encoding="utf-8")
log_file.write(f"\n\n=== Run started at {datetime.now().isoformat()} ===\n")

def log(msg):
    print(msg)
    log_file.write(msg + "\n")
    log_file.flush()

### Check required files
missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    log("Error: The following required files are missing:")
    for f in missing_files:
        log(f" - {f}")
    log_file.close()
    sys.exit(1)
else:
    log(f"All required files are present: {required_files}\n")

### Run each script
for script_file in filtered_files:
    cmd = ["python", script_file]
    log(f"\n▶ Running: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            log(line.rstrip())

        process.wait()
        if process.returncode != 0:
            log(f"❌ Error occurred in: {script_file} (exit code {process.returncode})")
            log_file.close()
            sys.exit(1)
        else:
            log(f"✅ Completed: {script_file}")

    except Exception as e:
        log(f"❌ Exception running {script_file}: {str(e)}")
        log_file.close()
        sys.exit(1)

log(f"\n✅ All scripts completed successfully at {datetime.now().isoformat()}")
log_file.close()
