from ultralytics import YOLO
import cv2
import os

# Lazy load model variables
_model = None
_model_load_attempted = False

def get_yolo_model():
    global _model, _model_load_attempted
    if _model is None and not _model_load_attempted:
        # Load the Pose model which can do BOTH detection (person) AND pose estimation
        model_path = "yolov8s-pose.pt"
        print(f"Loading YOLOv8 Pose model from {model_path}...")
        _model_load_attempted = True
        try:
            _model = YOLO(model_path)
            print("YOLOv8 Pose model loaded successfully.")
        except Exception as e:
            print(f"Error loading YOLOv8 Pose model: {e}")
            _model = None
    return _model

def detect_and_track_objects_in_frame(frame, conf_threshold=0.5):
    """
    Runs YOLOv8 object tracking and pose estimation on a single frame.
    
    Returns:
        List of dictionaries containing detected objects and their poses:
        [
            {
                "id": 1,
                "class": "person", 
                "confidence": 0.85,
                "bbox": [x1, y1, x2, y2],
                "keypoints": [[x, y, conf], ...] # 17 keypoints if person
            },
            ...
        ]
    """
    model = get_yolo_model()
    if model is None:
        raise RuntimeError("YOLO model is not initialized.")
        
    # Run tracking inference to maintain persistent IDs across frames
    results = model.track(frame, conf=conf_threshold, persist=True, verbose=False)
    
    detected_objects = []
    
    for r in results:
        boxes = r.boxes
        keypoints = r.keypoints if hasattr(r, 'keypoints') and r.keypoints is not None else None
        
        for i, box in enumerate(boxes):
            b = box.xyxy[0].tolist() 
            c = int(box.cls)
            class_name = model.names[c]
            conf = float(box.conf)
            
            # Extract tracking ID if it exists
            track_id = int(box.id[0]) if box.id is not None else -1
            
            obj_data = {
                "id": track_id,
                "class": class_name,
                "confidence": round(conf, 2),
                "bbox": [int(x) for x in b],
                "keypoints": None
            }
            
            # Extract pose keypoints for humans
            if keypoints is not None and class_name == "person":
                kp_data = keypoints.data[i].tolist() # List of [x, y, conf] for 17 joints
                obj_data["keypoints"] = kp_data
                
            detected_objects.append(obj_data)
            
    return detected_objects
