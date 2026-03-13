import sys, os, re, glob, wave
from pathlib import Path
import contractions
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY not found in .env file")

elevenlabs = ElevenLabs(api_key=api_key)

from elevenlabs import VoiceSettings

# Console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------- Slide parsing ----------
def read_slides_from_file(file_path: str):
    """Return list of slide blocks starting with '**Slide'."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    slides = re.split(r'(?=\*\*Slide)', text)
    return [s.strip() for s in slides if s.strip()]

def extract_slide_number(slide_block: str) -> int:
    """Extract numeric slide number from header like '**Slide 3 [12 sec]:'."""
    first_line = slide_block.splitlines()[0].strip()
    m = re.match(r"\*\*Slide\s+(\d+)", first_line)
    if not m:
        raise ValueError(f"Could not extract slide number from header: {first_line}")
    return int(m.group(1))

def remove_header(slide_block: str) -> str:
    """Strip the first '**Slide' header line + trailing asterisks."""
    lines = slide_block.splitlines()
    if lines and lines[0].strip().startswith("**Slide"):
        lines = lines[1:]
    narration = "\n".join(lines).strip().rstrip("*").strip()
    return narration

# ---------- ElevenLabs TTS ----------
def elevenlabs_tts(text: str, out_path: str, voice_id: str):
    """
    Convert text → speech via ElevenLabs and save as proper WAV file.
    """
    text = text.replace("`", "'").replace("’", "'").replace("‘", "'")
    clean_text = contractions.fix(text)

    resp = elevenlabs.text_to_speech.convert(
        voice_id=voice_id,
        text=clean_text,
        model_id="eleven_turbo_v2",
        output_format="pcm_16000",
        voice_settings=VoiceSettings(
            speed=0.98,
            stability=0.88,
            similarity_boost=0.60,
        ),
    )

    pcm_bytes = b"".join([chunk for chunk in resp if chunk])

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm_bytes)

    print(f'Audio written → "{out_path}"')

# ---------- Main ----------
if __name__ == "__main__":
    scriptfile = "script.txt"
    input_file = scriptfile

    slides = read_slides_from_file(input_file)
    num_slides = len(slides)
    print(f"Total slide blocks in {input_file}: {num_slides}")

    # Your ElevenLabs voice_id (replace with your actual ID string)
    #VOICE_ID = "oVJIKtwMNyVoaGgYBKDc" #Yusri - Snowball Mic 2
    VOICE_ID = "9x6m5PBXrn5YLEWGif5F" #Yusri - Rode NT1
    #VOICE_ID = "15Y62ZlO8it2f5wduybx" #Shazrina 
    #VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2" #Alice - Clear, Engaging Educator"

    # Clean old WAVs
    for file in glob.glob("slide*.wav"):
        os.remove(file)

    # Generate
    for slide in slides:
        try:
            slide_num = extract_slide_number(slide)
            narration = remove_header(slide)
            out_file = f"slide{slide_num}.wav"
            elevenlabs_tts(narration, out_file, VOICE_ID)
        except Exception as e:
            print(f"Error processing slide block: {e}")

    produced_files = glob.glob("slide*.wav")
    print(f"Produced {len(produced_files)} WAV files.")