from gpt4all import GPT4All
import json
import re

# Lazy load model variables
_model = None
_model_load_attempted = False

def get_llm_model():
    global _model, _model_load_attempted
    if _model is None and not _model_load_attempted:
        print("Initializing LLM for prompt parsing...")
        _model_load_attempted = True
        try:
            # We use a 3 Billion parameter model for faster CPU inference
            _model = GPT4All("orca-mini-3b-gguf2-q4_0.gguf") 
            print("LLM loaded successfully.")
        except Exception as e:
            print(f"Error loading LLM: {e}")
            _model = None
    return _model

def parse_prompt(query):
    """
    Uses a local LLM to parse a natural language query into structured JSON.
    Example: "Find a red car" -> {"object": "car", "color": "red", "anomaly": null}
    """
    # Fast path: Check if we can just use the instant heuristic parser for simple queries
    heuristic_result = _heuristic_parse(query)
    
    # If the user's query is very short or the heuristic found an object and color,
    # it's usually a simple query and we can return it instantly without keeping the user waiting!
    word_count = len(query.strip().split())
    if heuristic_result["object"] is not None and (heuristic_result["color"] is not None or heuristic_result["anomaly"] is not None or word_count <= 4):
        print("Using instant heuristic parser for simple query.")
        return heuristic_result

    model = get_llm_model()
    if model is None:
        # Fallback heuristic if LLM fails to load
        return heuristic_result
        
    system_prompt = """You are an AI assistant for a CCTV video analysis system.
Your task is to extract information from the user's search query and output ONLY valid JSON.
Extract these keys if present:
- "object": The main physical object they are looking for (e.g. "car", "person", "truck", "bag"). Use standard COCO dataset names if possible.
- "color": The master color of the object, if specified (e.g. "red", "blue", "black").
- "anomaly": Any specific behavior or action mentioned (e.g. "running", "parked", "fighting", "sitting"). If none, use null.
- "attributes": A string containing specific clothing items, accessories, or secondary descriptors mentioned (e.g. "blue hat", "spectacles", "red backpack"). If none, use null.

Output exactly a JSON object and nothing else."""

    user_prompt = f"Query: \"{query}\"\nOutput JSON:"
    
    try:
        # Generate response
        with model.chat_session(system_prompt=system_prompt):
            # Limit the prompt size even further, dropping temp to 0.0 for speed and accuracy
            response = model.generate(user_prompt, max_tokens=80, temp=0.0)
            
        print(f"LLM Raw Output: {response}")
        
        # Try to extract JSON from the text in case the LLM wrapped it in markdown
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            # Ensure keys exist
            return {
                "object": parsed.get("object") or heuristic_result.get("object"),
                "color": parsed.get("color") or heuristic_result.get("color"),
                "anomaly": parsed.get("anomaly"),
                "attributes": parsed.get("attributes")
            }
        else:
            print("Failed to parse JSON from LLM output. Falling back to heuristic.")
            return heuristic_result
            
    except Exception as e:
        print(f"Error during LLM inference: {e}")
        return heuristic_result

def _heuristic_parse(query):
    """
    A dumb fallback regex/keyword parser if the LLM isn't working or is too slow.
    """
    query = query.lower()
    
    colors = ["red", "blue", "green", "black", "white", "yellow", "gray", "silver", "orange", "purple", "brown"]
    objects = ["car", "person", "man", "woman", "guy", "boy", "girl", "truck", "bus", "bicycle", "motorcycle", "bag", "backpack", "dog", "cat"]
    
    extracted = {
        "object": None,
        "color": None,
        "anomaly": None,
        "attributes": None
    }
    
    for c in colors:
        if c in query:
            extracted["color"] = c
            break
            
    for o in objects:
        if o in query:
            # Map common synonyms to COCO classes
            if o in ["person", "man", "woman", "guy", "boy", "girl"]: 
                extracted["object"] = "person"
                # If we have a color and it's a person, treat it as an attribute 
                # (e.g. "red shirt") to trigger CLIP instead of simple K-Means
                if extracted["color"]:
                    # Check for explicit shirt/clothes mention or just use color
                    if "shirt" in query:
                        extracted["attributes"] = f"{extracted['color']} shirt"
                    elif "hoodie" in query:
                        extracted["attributes"] = f"{extracted['color']} hoodie"
                    elif "jacket" in query:
                        extracted["attributes"] = f"{extracted['color']} jacket"
                    else:
                        extracted["attributes"] = f"{extracted['color']} clothing"
            else:
                extracted["object"] = o
            break
            
    # Quick keyword checks for anomalies/actions
    actions = ["running", "walking", "parked", "standing", "abandoned", "fighting", "falling", "sitting"]
    for a in actions:
        if a in query:
            extracted["anomaly"] = a
            break
            
    return extracted

if __name__ == "__main__":
    # Test script
    test_queries = [
        "Find a red car parked",
        "Person wearing a blue shirt",
        "a guy with a green hoodie",
        "a girl with a red jacket",
        "a man in black",
        "A black backpack left behind"
    ]
    print("\n--- Testing NLP Parser ---")
    for q in test_queries:
        print(f"Query: \"{q}\"")
        res = parse_prompt(q)
        print(f"Parsed: {res}\n")
