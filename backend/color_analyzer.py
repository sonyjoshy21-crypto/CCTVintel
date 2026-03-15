
import cv2
import numpy as np
from sklearn.cluster import KMeans

# Pre-defined basic colors and their RGB values for simple matching
COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "brown": (165, 42, 42),
    "maroon": (128, 0, 0),
    "navy": (0, 0, 128),
    "olive": (128, 128, 0),
    "teal": (0, 128, 128),
    "silver": (192, 192, 192),
    "gold": (255, 215, 0),
    "beige": (245, 245, 220)
}

# Mapping of shades back to basic colors for the query matching
COLOR_MAP = {
    "maroon": "red",
    "navy": "blue",
    "olive": "green",
    "teal": "cyan",
    "silver": "white",
    "gold": "yellow",
    "beige": "white"
}

def get_mapped_color(color_name):
    """Maps a specific shade back to a basic color name."""
    return COLOR_MAP.get(color_name.lower(), color_name.lower())

def get_dominant_color(image, k=3):
    """
    Extracts the color distribution from an image crop.
    Returns: Dictionary of {color_name: percentage}
    """
    if image is None or image.size == 0:
        return {"unknown": 1.0}
        
    # Convert image from BGR to RGB for K-Means
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pixels = img_rgb.reshape((-1, 3))
    
    # Filter out near-black or near-white pixels if they aren't the majority
    mask = np.any((pixels > 20) & (pixels < 240), axis=1)
    if not np.any(mask) or np.mean(mask) < 0.1:
        mask = np.ones(len(pixels), dtype=bool)
    filtered_pixels = pixels[mask]
    
    if len(filtered_pixels) < k:
        filtered_pixels = pixels
    
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)
    
    # Find color distribution
    counts = np.bincount(kmeans.labels_)
    total = np.sum(counts)
    
    distribution = {}
    for i in range(k):
        rgb = kmeans.cluster_centers_[i]
        weight = counts[i] / total
        
        # Convert RGB to color name
        rgb_pixel = np.uint8([[rgb]])
        hsv_pixel = cv2.cvtColor(rgb_pixel, cv2.COLOR_RGB2HSV)[0][0]
        h, s, v = hsv_pixel
        
        # Mapping logic
        if v < 50: name = "black"
        elif s < 45 and v > 150: name = "white"
        elif s < 45: name = "gray"
        elif (h < 10) or (h > 170): name = "red"
        elif h < 22: name = "orange"
        elif h < 38: name = "yellow"
        elif h < 85: name = "green"
        elif h < 135: name = "blue"
        elif h < 170: name = "purple"
        else: name = "red"
        
        distribution[name] = distribution.get(name, 0) + weight
        
    # Sort by percentage
    return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))

def analyze_object_attributes(frame, bbox, object_type="unknown"):
    """
    Analyzes attributes (like color) of a specific object in a frame.
    Returns: Dictionary including the most dominant color and full distribution.
    """
    x1, y1, x2, y2 = bbox
    
    # Ensure coordinates are within frame bounds
    h, w, _ = frame.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if x2 <= x1 or y2 <= y1:
        return {"color": "unknown", "distribution": {}}
        
    # Crop the object from the frame
    object_crop = frame[y1:y2, x1:x2]
    h_c, w_c = object_crop.shape[:2]
    
    if object_type == "person":
        cy1, cy2 = int(h_c * 0.25), int(h_c * 0.60)
        cx1, cx2 = int(w_c * 0.20), int(w_c * 0.80)
    else:
        cy1, cy2 = int(h_c * 0.2), int(h_c * 0.8)
        cx1, cx2 = int(w_c * 0.2), int(w_c * 0.8)

    if cx2 > cx1 and cy2 > cy1:
        object_crop = object_crop[cy1:cy2, cx1:cx2]
    
    # Extract distribution
    distribution = get_dominant_color(object_crop)
    top_color = list(distribution.keys())[0] if distribution else "unknown"
    
    return {"color": top_color, "distribution": distribution}
    x1, y1, x2, y2 = bbox
    
    # Ensure coordinates are within frame bounds
    h, w, _ = frame.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if x2 <= x1 or y2 <= y1:
        return {"color": "unknown"}
        
    # Crop the object from the frame
    object_crop = frame[y1:y2, x1:x2]
    
    # ADVANCED CROPPING LOGIC
    h_c, w_c = object_crop.shape[:2]
    
    if object_type == "person":
        # Target the Torso: 25% down to 60% down
        # This isolates the shirt/top while avoiding hair (top) and pants/shoes (bottom)
        cy1, cy2 = int(h_c * 0.25), int(h_c * 0.60)
        cx1, cx2 = int(w_c * 0.20), int(w_c * 0.80) # Avoid background at sides
    else:
        # Standard object (cars, etc.): Grab the inner 60%
        cy1, cy2 = int(h_c * 0.2), int(h_c * 0.8)
        cx1, cx2 = int(w_c * 0.2), int(w_c * 0.8)

    if cx2 > cx1 and cy2 > cy1:
        object_crop = object_crop[cy1:cy2, cx1:cx2]
    
    # Extract dominant color
    color = get_dominant_color(object_crop)
    
    return {"color": color}
