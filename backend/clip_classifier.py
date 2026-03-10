import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# Lazy load model variables
_clip_model = None
_clip_processor = None
_model_load_attempted = False

def get_clip_model():
    global _clip_model, _clip_processor, _model_load_attempted
    if _clip_model is None and not _model_load_attempted:
        print("Loading CLIP model for zero-shot attribute classification...")
        _model_load_attempted = True
        try:
            # Load the standard OpenAI CLIP model
            model_id = "openai/clip-vit-base-patch32"
            _clip_model = CLIPModel.from_pretrained(model_id)
            _clip_processor = CLIPProcessor.from_pretrained(model_id)
            print("CLIP model loaded successfully.")
        except Exception as e:
            print(f"Error loading CLIP model: {e}")
            _clip_model = None
            _clip_processor = None
    return _clip_model, _clip_processor

def classify_attributes(image_rgb, text_prompts):
    """
    Classifies a cropped RGB image using CLIP against a list of text prompts.
    
    Args:
        image_rgb: A cropped RGB image (numpy array or PIL Image)
        text_prompts: List of descriptive strings (e.g., ["a person with a blue hat", "a person with no hat"])
        
    Returns:
        The string prompt from text_prompts that had the highest probability match, 
        or None if model couldn't be loaded.
    """
    model, processor = get_clip_model()
    
    if model is None or processor is None:
        return None
        
    try:
        # If it's a numpy array from OpenCV, convert to PIL
        if not isinstance(image_rgb, Image.Image):
            image = Image.fromarray(image_rgb)
        else:
            image = image_rgb
            
        # Prepare inputs for the model
        inputs = processor(text=text_prompts, images=image, return_tensors="pt", padding=True)
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            
        # CLIP computes logits per image and per text
        logits_per_image = outputs.logits_per_image # this is the image-text similarity score
        probs = logits_per_image.softmax(dim=1) # normalize to probabilities
        
        # Get index of the max probability
        best_match_idx = probs.argmax().item()
        return text_prompts[best_match_idx]
        
    except Exception as e:
        print(f"Error during CLIP classification: {e}")
        return None
