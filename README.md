# CCTVIntel 

CCTVIntel is an AI-powered video analysis platform that enables users to upload CCTV footage and perform intelligent searches using natural language prompts (e.g., "Find a red car" or "Person running").

## Prerequisites to Run on Another System

To run this project on a new system, you will need to have installed:
- **Python 3.10+**
- **Node.js (v20.19+ or 22.12+)**
- **Git** (optional, for cloning)

---

## 🚀 Setup Instructions

### 1. Download/Copy the Project
Copy the entire `CCTVIntel` folder to your new machine (you can zip it up and transfer it via Google Drive, a USB stick, or GitHub).

> **Note:** Do NOT copy the `backend/venv` or `frontend/node_modules` folders, as they are large and OS-specific. You will recreate them on the new machine.

### 2. Setup the Backend (Python)

Open a terminal and navigate to the backend folder:
```bash
cd CCTVIntel/backend
```

Create a fresh virtual environment:
**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages:
```bash
pip install -r requirements.txt
```

Start the Flask Server:
```bash
python app.py
```
*(Note: The first time you run a query, the system will automatically download the YOLOv8 AI weights and the GPT4All LLM weights to the new machine. This may take a few minutes depending on internet speed).*

### 3. Setup the Frontend (React / Vite)

Open a **new** terminal window and navigate to the frontend folder:
```bash
cd CCTVIntel/frontend
```

Install the Node modules:
```bash
npm install
```

Start the React Development Server:
```bash
npm run dev
```

### 4. Use the App!
Open your web browser and go to `http://localhost:5173`. You can now upload a video and search through it using natural language!
