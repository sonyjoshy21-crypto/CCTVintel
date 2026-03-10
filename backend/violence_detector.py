import cv2
import numpy as np
from collections import deque
import os
import tensorflow as tf
from tensorflow.keras import backend as K

def preprocess_input(img):
    """ Mimic the transforms.py processing logic """
    dim = 256
    (h, w) = img.shape[:2]
    if h > w:
        r = dim / float(w)
        reDim = (dim, int(h * r))
    else:      
        r = dim / float(h)
        reDim = (int(w * r), dim)
    
    # Resize
    resized = cv2.resize(img, reDim, interpolation=cv2.INTER_LINEAR)
    
    # Center Crop to 224x224
    h, w = resized.shape[:2]
    y = int((h - 224)/2)
    x = int((w - 224)/2)
    cropped = resized[y:(224+y), x:(224+x)]
    
    # Normalize
    return (cropped / 255.) * 2 - 1

def load_violence_model(model_path):
    print("Loading the complete exported Keras model for violence detection...")
    tf.keras.config.enable_unsafe_deserialization()
    import builtins
    builtins.K = K
    model = tf.keras.models.load_model(model_path)
    print("Violence Model loaded successfully!")
    return model

def classify_clip(model, clip):
    """ Perform Inference on the clip of 16 frames """
    processed_clip = np.array([preprocess_input(f) for f in clip])
    processed_clip = np.expand_dims(processed_clip, axis=0) # Shape: (1, 16, 224, 224, 3)

    # 1. Predict
    predictions = model.predict(processed_clip, verbose=0)[0]
    
    # 2. Label conversion matching logic
    threshold = 0.20
    idx = np.argmax(predictions)
    
    if idx == 1 and predictions[1] < threshold:
        idx = 0
    elif idx == 0 and (1.0 - predictions[0]) > threshold:
        idx = 1
        
    labels = ["NonViolence", "Violence"]
    return {'label': labels[idx], 'score': predictions[idx] * 100}

