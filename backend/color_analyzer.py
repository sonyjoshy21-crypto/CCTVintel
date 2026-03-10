
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
    "brown": (165, 42, 42)
}

def get_dominant_color(image, k=3):
    """
    Extracts the dominant color from an image crop using K-Means clustering.
    
    Args:
        image: OpenCV BGR image crop (e.g., of an object)
        k: Number of color clusters
        
    Returns:
        String name of the closest basic color
    """
    if image is None or image.size == 0:
        return "unknown"
        
    # Convert image from BGR to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Reshape the image to be a list of pixels
    pixels = image.reshape((-1, 3))
    
    # Filter out near-black or near-white pixels (often background/shadows)
    # Simple heuristic to focus on the actual object color
    mask = np.any((pixels > 20) & (pixels < 240), axis=1)
    if not np.any(mask): # If all pixels are black/white, just use all
        mask = np.ones(len(pixels), dtype=bool)
        
    filtered_pixels = pixels[mask]
    
    # If image is too small or flat, default back
    if len(filtered_pixels) < k:
        filtered_pixels = pixels
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(filtered_pixels)
    
    # Find the most frequent cluster label
    counts = np.bincount(labels)
    dominant_cluster_index = np.argmax(counts)
    
    # Get the RGB value of the dominant cluster center
    dominant_color_rgb = kmeans.cluster_centers_[dominant_cluster_index]
    
    # Find the closest matching basic color name
    min_dist = float('inf')
    closest_color_name = "unknown"
    
    for name, static_rgb in COLORS.items():
        # Calculate Euclidean distance between the dominant color and predefined colors
        dist = np.linalg.norm(dominant_color_rgb - np.array(static_rgb))
        if dist < min_dist:
            min_dist = dist
            closest_color_name = name
            
    return closest_color_name

def analyze_object_attributes(frame, bbox):
    """
    Analyzes attributes (like color) of a specific object in a frame.
    
    Args:
        frame: Full OpenCV BGR frame
        bbox: Bounding box [x1, y1, x2, y2]
        
    Returns:
        Dictionary of attributes (e.g., {"color": "red"})
    """
    x1, y1, x2, y2 = bbox
    
    # Ensure coordinates are within frame bounds
    h, w, _ = frame.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if x2 <= x1 or y2 <= y1:
        return {"color": "unknown"}
        
    # Crop the object from the frame
    object_crop = frame[y1:y2, x1:x2]
    
    # Grab the inner 60% of the bounding box to avoid occluding objects at the edges
    # This ensures that if a person is standing IN FRONT of a car, we analyze the center
    # of the bounding box where the car's roof/hood is more likely to be visible, rather 
    # than the person's clothes at the bottom/side boundaries.
    h_c, w_c = object_crop.shape[:2]
    cx1, cx2 = int(w_c * 0.2), int(w_c * 0.8)
    cy1, cy2 = int(h_c * 0.2), int(h_c * 0.8)
    if cx2 > cx1 and cy2 > cy1:
        object_crop = object_crop[cy1:cy2, cx1:cx2]
    
    # Extract dominant color
    color = get_dominant_color(object_crop)
    
    return {"color": color}
