from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
from video_processor import analyze_video

app = Flask(__name__)
# Enable CORS for the React frontend
CORS(app)

# Global dictionary to store analysis progress in memory
analysis_progress = {}

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__name__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "CCTVIntel API is running"}), 200

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    try:
        # Secure the filename or generate a unique ID, but for now just save it
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return jsonify({
            "message": "Upload successful", 
            "filename": file.filename, 
            "filepath": filepath
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import send_from_directory

@app.route('/api/video/<filename>', methods=['GET'])
def get_video(filename):
    """Serves the generated annotated video file to the frontend application."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, conditional=True)

@app.route('/api/progress/<filename>', methods=['GET'])
def get_progress(filename):
    """Returns the current analysis progress for a given filename."""
    progress_data = analysis_progress.get(filename, {"status": "not_started", "percent": 0, "message": "Waiting to start..."})
    return jsonify(progress_data), 200

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    if not data or 'filename' not in data or 'query' not in data:
        return jsonify({"error": "Missing filename or query"}), 400
        
    filename = data['filename']
    query = data['query']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": f"Uploaded video {filename} not found."}), 404
        
    try:
        print(f"Analyzing {filename} with query: {query}")
        frame_skip = data.get('frame_skip', 5) # Default to 5 if not provided
        
        # Initialize progress for this file
        analysis_progress[filename] = {"status": "analyzing", "percent": 0, "message": "Parsing query with Deep Learning..."}
        
        # Define a callback function to update progress
        def update_progress(percent, message=None):
            current_message = message if message else analysis_progress[filename].get("message", "Processing video frames...")
            analysis_progress[filename] = {"status": "analyzing", "percent": percent, "message": current_message}
            
        result = analyze_video(filepath, query, frame_skip=frame_skip, progress_callback=update_progress)
        
        # Mark as complete
        analysis_progress[filename] = {"status": "completed", "percent": 100, "message": "Analysis complete!"}
        
        return jsonify(result), 200
    except Exception as e:
        # Mark as error
        analysis_progress[filename] = {"status": "error", "percent": 0, "message": f"Error: {str(e)}"}
        traceback.print_exc()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, port=5000)
