import cv2
import os

import threading

# Lazy load model variables
_obj_model = None
_pose_model = None
_models_load_attempted = False
_load_lock = threading.Lock()

def get_yolo_models(progress_callback=None):
    global _obj_model, _pose_model, _models_load_attempted
    
    with _load_lock:
        if not _models_load_attempted:
            try:
                from ultralytics import YOLO
                
                # 1. Load standard object detection model
                obj_model_path = "yolov8n.pt"
                if not os.path.exists(obj_model_path) and progress_callback:
                    progress_callback(10, "Downloading AI Weights...", detail="Downloading yolov8n.pt (approx 6.2MB)...", category="system")
                _obj_model = YOLO(obj_model_path)
                
                # 2. Load the Pose model
                pose_model_path = "yolov8s-pose.pt"
                if not os.path.exists(pose_model_path) and progress_callback:
                    progress_callback(10, "Downloading AI Weights...", detail="Downloading yolov8s-pose.pt (approx 25MB)... This may take a minute.", category="system")
                _pose_model = YOLO(pose_model_path)
                
                _models_load_attempted = True
            except Exception as e:
                print(f"CRITICAL MODEL LOAD ERROR: {e}")
                if progress_callback:
                    progress_callback(10, "Model Load Failed", detail=f"Error: {str(e)}", category="error")
                # Reset so we can try again on next request
                _models_load_attempted = False
                raise e
                
    return _obj_model, _pose_model

def detect_and_track_objects_in_frame(frame, conf_threshold=0.3, needs_pose=False):
    """
    Runs YOLOv8 object tracking on a single frame.
    If needs_pose is True, it runs a secondary pass to extract human pose keypoints.
    """
    obj_model, pose_model = get_yolo_models()
    if obj_model is None:
        raise RuntimeError("YOLO object model is not initialized.")
        
    # 1. Run standard object tracking for all classes
    # We use persist=True to let YOLO (ByteTrack) keep track IDs internally
    results = obj_model.track(frame, conf=conf_threshold, persist=True, verbose=False)
    
    detected_objects = []
    people_bboxes = []
    
    for r in results:
        boxes = r.boxes
        
        for i, box in enumerate(boxes):
            b = box.xyxy[0].tolist() 
            c = int(box.cls)
            class_name = obj_model.names[c]
            conf = float(box.conf)
            
            # Extract tracking ID if it exists
            track_id = int(box.id[0]) if box.id is not None else -1
            bbox_int = [int(x) for x in b]
            
            obj_data = {
                "id": track_id,
                "class": class_name,
                "confidence": round(conf, 2),
                "bbox": bbox_int,
                "keypoints": None
            }
            
            if class_name == "person":
                people_bboxes.append((obj_data, b))
                
            detected_objects.append(obj_data)
            
    # 2. If pose is needed for the query, run the pose model specifically
    if needs_pose and pose_model is not None and people_bboxes:
        # Running the pose model across the full frame to get keypoints
        # (It's often faster/cleaner than cropping every person, though dual-inference is heavy)
        pose_results = pose_model(frame, conf=0.4, verbose=False)
        for pr in pose_results:
            p_boxes = pr.boxes
            p_kps = pr.keypoints
            
            if p_kps is not None:
                for idx, p_box in enumerate(p_boxes):
                    pb = p_box.xyxy[0].tolist()
                    
                    # Match pose bounding boxes (pb) to object tracking boxes (b) using IoU or simple box center proximity
                    px_center = (pb[0] + pb[2]) / 2
                    py_center = (pb[1] + pb[3]) / 2
                    
                    for person_dict, orig_b in people_bboxes:
                        if person_dict["keypoints"] is not None:
                            continue # Already mapped
                            
                        # If the pose bounding box center is inside the tracking bounding box
                        if orig_b[0] <= px_center <= orig_b[2] and orig_b[1] <= py_center <= orig_b[3]:
                            person_dict["keypoints"] = p_kps.data[idx].tolist()
                            break
                            
    return detected_objects
