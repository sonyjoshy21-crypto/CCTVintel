from ultralytics import YOLO
import cv2
import os

# Lazy load model variables
_obj_model = None
_pose_model = None
_models_load_attempted = False

def get_yolo_models():
    global _obj_model, _pose_model, _models_load_attempted
    if not _models_load_attempted:
        _models_load_attempted = True
        
        # Load standard object detection model (80 COCO classes: cars, dogs, etc)
        obj_model_path = "yolov8n.pt" # Or 'yolov8s.pt' if you prefer higher accuracy
        try:
            print(f"Loading YOLOv8 Object model from {obj_model_path}...")
            _obj_model = YOLO(obj_model_path)
        except Exception as e:
            print(f"Error loading {obj_model_path}: {e}")
            
        # Load the Pose model strictly for human keypoints
        pose_model_path = "yolov8s-pose.pt"
        try:
            print(f"Loading YOLOv8 Pose model from {pose_model_path}...")
            _pose_model = YOLO(pose_model_path)
        except Exception as e:
            print(f"Error loading {pose_model_path}: {e}")
            
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
