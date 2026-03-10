import os
import sys

# Change cwd to the backend directory so that ultralytics/yolo paths and models load
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from video_processor import analyze_video
import json

video_path = r"c:\Users\basil\OneDrive\Desktop\basil\my_violence_detection\packaged_model_version\test_video.mp4"
query = "find violence and fights in the video"

print("Starting test...")
def progress(pct, msg):
    print(f"PROGRESS: {pct}% - {msg}")

result = analyze_video(video_path, query, progress_callback=progress)

print("\n=== FINAL RESULT ===")
print(json.dumps(result, indent=2))
