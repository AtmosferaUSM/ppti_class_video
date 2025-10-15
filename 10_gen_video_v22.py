import os, sys, time
import re
import numpy as np
import moviepy.editor as mp
from pdf2image import convert_from_path
import sys

#sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
    

videofile = f"slides.mp4"
lecture_topic_name = ""

try:
    os.remove('slides.mp4')
except:
    pass    

#def create_video(output_filename):
"""
Creates an MP4 video from slide PDF and audio WAV files.
Assumes files are named slideX.pdf and slideX.wav in the current directory,
where X is a sequential number.
"""
output_filename = videofile;
# 1. Get all PDF and WAV files, and sort them by slide number
pdf_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf") and re.match(r"slide\d+\.pdf", f, re.IGNORECASE)],key=lambda x: int(re.search(r'\d+', x).group()))

wav_files = sorted([f for f in os.listdir(".") if f.endswith(".wav") and re.match(r"slide\d+\.wav", f, re.IGNORECASE)], key=lambda x: int(re.search(r'\d+', x).group()))

if not pdf_files or not wav_files:
    print("Error: No PDF or WAV files found, or naming convention incorrect. Make sure they start with 'slide' and end with the correct extension.")
    #return
    sys.exit(1)

if len(pdf_files) != len(wav_files):
    print(f'len(pdf_files)={len(pdf_files)}; len(wav_files)={len(wav_files)}')
    print("Error: Number of PDF and WAV files does not match. To abort.")
    os._exit(1)
else:
    print(f'len(pdf_files)={len(pdf_files)}; len(wav_files)={len(wav_files)}')
    print("Number of PDF and WAV tallies. To generate video ...")

image_clips = []; audio_clips = []

for pdf_file, wav_file in zip(pdf_files, wav_files):
    # Ensure that both files exist
    if not (os.path.exists(pdf_file) and os.path.exists(wav_file)):
        print(f"Error: Both {pdf_file} and {wav_file} must exist. Abort.")
        os._exit(1)
        #continue
    try:
        images = convert_from_path(pdf_file, dpi=200)  # Convert PDF to image(s)
        if images:
            image = images[0]  # Use the first page of the PDF
            # Convert image to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            # Convert the PIL image to a NumPy array for moviepy
            image_array = np.array(image)
            audio_clip = mp.AudioFileClip(wav_file)
            image_clip = mp.ImageClip(image_array).set_duration(audio_clip.duration)
            image_clips.append(image_clip)
            audio_clips.append(audio_clip)
            print(f'processing {pdf_file, wav_file}')
        else:
            print(f"Error: Could not convert PDF {pdf_file} to image.")
            continue
    except Exception as e:
        print(f"Error processing {pdf_file} or {wav_file}: {e}")
        print("os.path.exists(pdf_file)",os.path.exists(pdf_file) )
        print("os.path.exists(wav_file)",os.path.exists(wav_file))
        print('')
        continue

# 3. Concatenate image clips into a video

if not image_clips:
    print("No valid image clips found. Cannot create video.")
    #return
    sys.exit(1)

try:
    final_clip = mp.concatenate_videoclips(image_clips, method="compose")
    # 4. Combine audio clips into a single audio track
    final_audio = mp.concatenate_audioclips(audio_clips)
    # 5. Attach the audio to the video
    final_clip = final_clip.set_audio(final_audio)
    # 6. Write the video file
    final_clip.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")
    print(f"Video created successfully: {output_filename}")
except Exception as e:
    print(f"An error occurred during video creation: {e}")
finally:
    # Close all clips to release resources
    if 'final_clip' in locals():
        final_clip.close()
    if 'final_audio' in locals():
        final_audio.close()
    for clip in image_clips:
        clip.close()
    for clip in audio_clips:
        clip.close()
    print("Clips closed to release resources.")

time.sleep(3)  # wait for 2 seconds
#[os.remove(wav) or print(f"{wav} is removed.") for wav in wav_files]
#[os.remove(pdf) or print(f"{pdf} is removed.") for pdf in pdf_files]
#print(f"{wav_files} are removed.")
#print(f"{pdf_files} are removed.")

#if __name__ == "__main__":   
#    output_file = f"{videofile}"
#    create_video(output_file)
