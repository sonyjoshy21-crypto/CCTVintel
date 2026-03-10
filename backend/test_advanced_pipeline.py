import json
import time
from video_processor import analyze_video

def main():
    print("Testing the advanced video analysis pipeline...")
    
    # Needs a real video
    video_path = "uploads/download.mp4" 
    
    # Complex query that tests CLIP and Tracking
    # Use "person" since we don't have "guy" explicitly in the test video (assuming standard person detection)
    query = "a person with dark hair running"
    
    print(f"\n--- Running Test ---")
    print(f"Video: {video_path}")
    print(f"Query: {query}")
    
    def on_progress(percent, msg):
        print(f"[{percent}%] {msg}")
        
    try:
        start_time = time.time()
        result = analyze_video(
            video_path=video_path,
            query=query,
            progress_callback=on_progress
        )
        end_time = time.time()
        
        print(f"\n--- Test Finished in {end_time - start_time:.2f}s ---")
        print("\nResults Summary:")
        print(f"Status: {result.get('status')}")
        print(f"Matches Found: {result.get('matches_found')}")
        print(f"Generated Video: {result.get('annotated_video_path')}")
        
        print("\nFirst 3 Matches:")
        for r in result.get('results', [])[:3]:
            print(f" - [{r['timestamp']}s] ID:{r.get('track_id')} Action:{r.get('action')} Attributes:{r.get('attributes')}")
            
    except Exception as e:
        print(f"\n--- Error during Test ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
