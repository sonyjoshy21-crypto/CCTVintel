from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import traceback
from video_processor import analyze_video

import logging

# Silence Flask/Werkzeug terminal spam
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
# Enable CORS for the React frontend
CORS(app)

# Global dictionary to store analysis progress in memory
analysis_progress = {}
# Segmented logs for the Desktop Monitor
ai_logs = []
sys_logs = []
app_logs = [] # Legacy compatibility

def add_log(message, category="system"):
    """Adds a timestamped log message to the appropriate category."""
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if category == "ai":
        ai_logs.append(log_entry)
        if len(ai_logs) > 300: ai_logs.pop(0)
    elif category == "error":
        sys_logs.append(f"!! ERROR !! {log_entry}")
    else:
        sys_logs.append(log_entry)
        if len(sys_logs) > 300: sys_logs.pop(0)
        
    # Also print to terminal for dev visibility
    print(f"{category.upper()}: {log_entry}")

def set_error(filename, error_msg):
    """Logs a critical failure and updates the analysis state."""
    add_log(f"CRITICAL FAILURE: {error_msg}", category="error")
    analysis_progress[filename] = {
        "status": "error", 
        "percent": 0, 
        "message": "Analysis Failed",
        "error_log": error_msg
    }

def reset_logs():
    """Clears all logs for a fresh analysis session."""
    global ai_logs, sys_logs
    ai_logs.clear()
    sys_logs.clear()
    add_log("--- NEW SESSION STARTED ---", category="system")

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

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Returns the segmented logs and current metrics for the Desktop Monitor."""
    # Find the first active analysis to get current metrics
    active_filename = next(iter(analysis_progress), None)
    metrics = {
        "percent": 0,
        "matches": 0,
        "stage": "Idle"
    }
    if active_filename:
        data = analysis_progress[active_filename]
        metrics["percent"] = data.get("percent", 0)
        metrics["matches"] = data.get("match_count", 0)
        metrics["stage"] = data.get("message", "Processing")
        
    return jsonify({
        "ai_logs": ai_logs,
        "sys_logs": sys_logs,
        "metrics": metrics
    }), 200

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
        reset_logs() # Clear old monitor logs for the new analysis
        print(f"Analyzing {filename} with query: {query}")
        frame_skip = data.get('frame_skip', 5) # Default to 5 if not provided
        
        # Initialize progress for this file
        analysis_progress[filename] = {
            "status": "analyzing", 
            "percent": 0, 
            "message": "Parsing query...",
            "match_count": 0
        }
        
        # Define a callback function to update progress
        def update_progress(percent, message=None, detail=None, category="system", matches=None):
            if message:
                analysis_progress[filename]["message"] = message
            analysis_progress[filename]["percent"] = percent
            if matches is not None:
                analysis_progress[filename]["match_count"] = matches
            
            if detail:
                add_log(detail, category=category)
            
        result = analyze_video(filepath, query, frame_skip=frame_skip, progress_callback=update_progress)
        
        # Mark as complete
        analysis_progress[filename] = {"status": "completed", "percent": 100, "message": "Analysis complete!"}
        
        return jsonify(result), 200
    except Exception as e:
        # Mark as error in both state and logs
        set_error(filename, str(e))
        traceback.print_exc()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, port=5000)
