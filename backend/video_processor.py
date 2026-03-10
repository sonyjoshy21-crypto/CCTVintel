import cv2
import os
import time
from collections import deque
from yolo_detector import detect_and_track_objects_in_frame
from color_analyzer import analyze_object_attributes
from clip_classifier import classify_attributes
from nlp_parser import parse_prompt
from action_tracker import SimpleTracker
from violence_detector import load_violence_model, classify_clip

def analyze_video(video_path, query, conf_threshold=0.25, frame_skip=5, progress_callback=None):
    """
    Analyzes a video for specific objects and attributes based on a natural language query.
    Generates an annotated output video.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    print(f"Parsing query: '{query}'")
    
    if progress_callback:
        progress_callback(5, "Querying Large Language Model...") 
    parsed_query = parse_prompt(query)
    target_object = parsed_query.get("object")
    target_color = parsed_query.get("color")
    target_anomaly = parsed_query.get("anomaly")
    target_attributes = parsed_query.get("attributes")
    
    print(f"Parsed Query JSON: {parsed_query}")
    
    check_violence = False
    violence_model = None
    if any(keyword in query.lower() for keyword in ["violence", "fight", "assault", "attack"]):
        check_violence = True
        
    if not target_object and not check_violence:
        return {
            "error": "Could not identify a target object or specific anomaly from the query.",
            "parsed_query": parsed_query,
            "results": []
        }
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps == 0 or fps != fps:
        fps = 30.0 
        
    # Setup Video Writer for Annotated Output
    output_filename = f"annotated_{os.path.basename(video_path)}"
    # Save it in the same directory as the upload for now
    output_path = os.path.join(os.path.dirname(video_path), output_filename)
    # H264 codec for web compatibility via mp4v or avc1
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out_video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
    if progress_callback:
        progress_callback(10, "Loading Video & Initializing Models...") 
        
    if check_violence:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "models", "saved_violence_model.keras")
        violence_model = load_violence_model(model_path)

    results_list = []
    frame_count = 0
    tracker = SimpleTracker(max_distance=100, max_disappeared=10)
    frame_buffer = deque(maxlen=16)
    violence_event_counter = -100 
    
    # Keep track of IDs we have already run through CLIP to save immense processing time
    clip_processed_ids = {}
    
    print(f"Starting video processing: {video_path} (FPS: {fps}, Total Frames: {total_frames})")
    start_time = time.time()
    last_reported_percent = 10
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        annotated_frame = frame.copy()
            
        if progress_callback and frame_count % 30 == 0 and total_frames > 0:
            current_percent = int(10 + (frame_count / total_frames) * 85)
            if current_percent > last_reported_percent:
                progress_callback(current_percent, f"Running AI Analysis (Frame {frame_count}/{total_frames})...")
                last_reported_percent = current_percent
            
        if check_violence:
            frame_buffer.append(frame)
            if len(frame_buffer) == 16 and frame_count % 16 == 0:
                prediction = classify_clip(violence_model, list(frame_buffer))
                if prediction['label'] == 'Violence':
                    timestamp_sec = frame_count / fps
                    results_list.append({
                        "timestamp": round(timestamp_sec, 2),
                        "frame_index": frame_count,
                        "object": "violence",
                        "confidence": float(prediction['score']),
                        "color": "unknown",
                        "action": "Violence Detected",
                        "speed": 0,
                        "bbox": [0, 0, width, height], # Full frame for violence
                        "track_id": violence_event_counter
                    })
                    violence_event_counter -= 1
                    
                    # Annotate frame for violence
                    cv2.rectangle(annotated_frame, (0, 0), (width, height), (0, 0, 255), 10)
                    cv2.putText(annotated_frame, "VIOLENCE DETECTED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)

        if frame_count % frame_skip == 0 and target_object:
            timestamp_sec = frame_count / fps
            
            # 1. Run Object Det + Tracking + Pose
            raw_detections = detect_and_track_objects_in_frame(frame, conf_threshold)
            
            valid_detections = []
            for det in raw_detections:
                c_name = det["class"]
                conf = det["confidence"]
                
                min_conf = 0.45 if c_name == "person" else conf_threshold
                if conf < min_conf:
                    continue
                    
                bx1, by1, bx2, by2 = det["bbox"]
                b_width = bx2 - bx1
                b_height = by2 - by1
                
                if b_width > 0:
                    aspect_ratio = b_height / b_width
                    if c_name in ["car", "truck", "bus"] and aspect_ratio > 1.5:
                        continue 
                        
                valid_detections.append(det)
                
            # 2. Update Basic Speed Tracker (using legacy format)
            # We use our tracker for speed, but rely on YOLO track IDs for identity
            tracker_input = [{"class": d["class"], "confidence": d["confidence"], "bbox": d["bbox"]} for d in valid_detections]
            speed_tracked = tracker.update(tracker_input, frame_count)
            
            # 3. Filter and Annotate
            for det, sp_det in zip(valid_detections, speed_tracked):
                if det["class"] == target_object:
                    match = True
                    color = "unknown"
                    action_label = sp_det.get("action", "unknown")
                    matched_attributes = None
                    
                    track_id = det["id"]
                    
                    # Handle Complex Attributes via CLIP
                    if target_attributes:
                        if track_id != -1 and track_id in clip_processed_ids:
                            # Re-use cached CLIP result for this tracked object to save massive time
                            matched_attributes = clip_processed_ids[track_id]
                        else:
                            # Run CLIP inference on the cropped bounding box
                            bx1, by1, bx2, by2 = det["bbox"]
                            # Add slight padding
                            pad = 10
                            crop_y1 = max(0, by1 - pad)
                            crop_y2 = min(height, by2 + pad)
                            crop_x1 = max(0, bx1 - pad)
                            crop_x2 = min(width, bx2 + pad)
                            
                            crop_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                            if crop_img.size > 0:
                                # Provide options: Does it have the attribute, or does it not?
                                prompts = [f"a person with {target_attributes}", f"a person without {target_attributes}"]
                                # Convert BGR to RGB for CLIP
                                crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
                                best_match = classify_attributes(crop_rgb, prompts)
                                
                                if best_match == prompts[0]:
                                    matched_attributes = target_attributes
                                else:
                                    matched_attributes = "no match"
                                    
                                if track_id != -1:
                                    clip_processed_ids[track_id] = matched_attributes
                        
                        if matched_attributes != target_attributes:
                            match = False

                    # Check basic color
                    if target_color and match:
                        attrs = analyze_object_attributes(frame, det["bbox"])
                        color = attrs.get("color", "unknown")
                        if color != target_color:
                            match = False
                            
                    # Check Actions & Pose (Sitting vs Running)
                    if target_anomaly and not check_violence and match:
                        anomaly_lower = target_anomaly.lower()
                        
                        # Handle Pose-based actions if it's a person and we have keypoints
                        if det["class"] == "person" and det["keypoints"] and len(det["keypoints"]) >= 17:
                            kps = det["keypoints"]
                            # Very simplified pose heuristic: 
                            # Keypoint 11=left hip, 12=right hip, 13=left knee, 14=right knee, 15=left ankle, 16=right ankle
                            l_hip, r_hip = kps[11], kps[12]
                            l_knee, r_knee = kps[13], kps[14]
                            
                            # Both knee confidences need to be somewhat high
                            if l_knee[2] > 0.5 and r_knee[2] > 0.5 and l_hip[2] > 0.5:
                                # If knees are close to hips in Y axis, it usually means sitting or crouching
                                avg_hip_y = (l_hip[1] + r_hip[1]) / 2
                                avg_knee_y = (l_knee[1] + r_knee[1]) / 2
                                
                                vertical_dist = abs(avg_hip_y - avg_knee_y)
                                # If vertical distance involves less than 15% of frame height, likely sitting
                                if vertical_dist < (height * 0.15):
                                    action_label = "sitting"
                                    
                        if anomaly_lower not in action_label.lower():
                            match = False
                            
                    if match:
                        results_list.append({
                            "timestamp": round(timestamp_sec, 2),
                            "frame_index": frame_count,
                            "object": det["class"],
                            "confidence": det["confidence"],
                            "color": color,
                            "action": action_label,
                            "attributes": matched_attributes,
                            "speed": sp_det.get("speed", 0),
                            "bbox": det["bbox"],
                            "track_id": track_id
                        })
                        
                        # Annotate the Match Frame
                        bx1, by1, bx2, by2 = det["bbox"]
                        color_box = (0, 255, 0) # Green for match
                        cv2.rectangle(annotated_frame, (bx1, by1), (bx2, by2), color_box, 3)
                        
                        label_text = f"ID:{track_id} {det['class']}"
                        if target_attributes and matched_attributes == target_attributes:
                            label_text += f" [{target_attributes}]"
                        if target_anomaly:
                            label_text += f" ({action_label})"
                            
                        cv2.putText(annotated_frame, label_text, (bx1, max(20, by1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_box, 2)
                        
                        # Draw Pose Keypoints if person
                        if det["keypoints"]:
                            for kp in det["keypoints"]:
                                x, y, conf = int(kp[0]), int(kp[1]), kp[2]
                                if conf > 0.5:
                                    cv2.circle(annotated_frame, (x, y), 4, (255, 0, 255), -1)

        # Write frame to output video (every frame, not just skipped ones)
        out_video.write(annotated_frame)
        frame_count += 1
        
    cap.release()
    out_video.release()
    process_time = time.time() - start_time
    print(f"Video processing finished in {process_time:.2f} seconds.")
    
    if progress_callback:
        progress_callback(98, "Formatting Final JSON Payload...") 
        
    unique_matches = []
    seen_track_ids = set()
    for res in results_list:
        tid = res["track_id"]
        # Allow negative track IDs (violence events) or first occurrences
        if tid < 0:
            unique_matches.append(res)
        elif tid not in seen_track_ids:
            unique_matches.append(res)
            seen_track_ids.add(tid)
            
    if progress_callback:
        progress_callback(100, "Done!") 
        
    return {
        "status": "success",
        "parsed_query": parsed_query,
        "processing_time_seconds": round(process_time, 2),
        "matches_found": len(unique_matches),
        "total_unfiltered_frames": len(results_list),
        "annotated_video_path": output_filename,
        "results": unique_matches
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        vid = sys.argv[1]
        q = sys.argv[2]
        res = analyze_video(vid, q)
        import json
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python video_processor.py <video_path> <query>")
