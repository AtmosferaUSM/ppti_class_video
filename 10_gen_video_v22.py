import os
import sys
import time
import re
import numpy as np
import moviepy.editor as mp
from pdf2image import convert_from_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

videofile = "slides.mp4"
DEFAULT_SLIDE_DURATION = 5.0  # seconds for silent slides

try:
    os.remove(videofile)
except FileNotFoundError:
    pass

"""
Creates an MP4 video from slide PDF and audio WAV files.
Assumes files are named slideX.pdf and slideX.wav in the current directory.
If slideX.wav is missing, the slide is shown silently for DEFAULT_SLIDE_DURATION.
"""

output_filename = videofile

# 1. Get all slide PDFs, sorted by slide number
pdf_files = sorted(
    [
        f for f in os.listdir(".")
        if f.endswith(".pdf") and re.match(r"slide\d+\.pdf", f, re.IGNORECASE)
    ],
    key=lambda x: int(re.search(r"\d+", x).group())
)

if not pdf_files:
    print("Error: No slide PDF files found.")
    sys.exit(1)

print(f"Found {len(pdf_files)} slide PDFs. Generating video ...")

video_clips = []
audio_clips_for_final = []

for pdf_file in pdf_files:
    slide_num = int(re.search(r"\d+", pdf_file).group())
    wav_file = f"slide{slide_num}.wav"

    if not os.path.exists(pdf_file):
        print(f"Warning: Missing PDF {pdf_file}. Skipping.")
        continue

    try:
        images = convert_from_path(pdf_file, dpi=200)
        if not images:
            print(f"Error: Could not convert PDF {pdf_file} to image.")
            continue

        image = images[0]
        if image.mode != "RGB":
            image = image.convert("RGB")

        image_array = np.array(image)

        if os.path.exists(wav_file):
            audio_clip = mp.AudioFileClip(wav_file)
            duration = audio_clip.duration
            image_clip = mp.ImageClip(image_array).set_duration(duration).set_audio(audio_clip)
            audio_clips_for_final.append(audio_clip)
            print(f"Processing narrated slide: {pdf_file} + {wav_file} ({duration:.2f} s)")
        else:
            duration = DEFAULT_SLIDE_DURATION
            image_clip = mp.ImageClip(image_array).set_duration(duration)
            print(f"Processing silent slide: {pdf_file} (no audio, {duration:.2f} s)")

        video_clips.append(image_clip)

    except Exception as e:
        print(f"Error processing {pdf_file}: {e}")
        continue

# 2. Concatenate video clips
if not video_clips:
    print("No valid video clips found. Cannot create video.")
    sys.exit(1)

try:
    final_clip = mp.concatenate_videoclips(video_clips, method="compose")

    # Audio is already attached per clip where it exists.
    # No need to separately concatenate audio and reattach globally.
    final_clip.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )
    print(f"Video created successfully: {output_filename}")

except Exception as e:
    print(f"An error occurred during video creation: {e}")

finally:
    if "final_clip" in locals():
        final_clip.close()

    for clip in video_clips:
        clip.close()

    for clip in audio_clips_for_final:
        clip.close()

    print("Clips closed to release resources.")

time.sleep(3)