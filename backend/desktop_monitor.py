import tkinter as tk
from tkinter import scrolledtext
import requests
import time
import threading

class LogMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTVIntel - Desktop AI Monitor")
        self.root.geometry("700x500")
        self.root.configure(bg="#1a1a1a")

        # Title Label
        title_label = tk.Label(
            root, text="Real-Time Process Diagnostics", 
            fg="#4fd1c5", bg="#1a1a1a", 
            font=("Consolas", 14, "bold"), pady=10
        )
        title_label.pack()

        # Log Area
        self.log_area = scrolledtext.ScrolledText(
            root, bg="#0d0d0d", fg="#d1d1d1", 
            font=("Consolas", 10), borderwidth=0, 
            padx=10, pady=10
        )
        self.log_area.pack(expand=True, fill='both', padx=15, pady=10)
        
        # Connection Status
        self.status_label = tk.Label(
            root, text="Connecting to backend...", 
            fg="#cbd5e0", bg="#1a1a1a", 
            font=("Consolas", 9), pady=5
        )
        self.status_label.pack()

        self.last_log_count = 0
        self.running = True
        
        # Start polling thread
        self.poll_thread = threading.Thread(target=self.poll_logs, daemon=True)
        self.poll_thread.start()

    def add_message(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def poll_logs(self):
        backend_url = "http://127.0.0.1:5000/api/logs"
        while self.running:
            try:
                response = requests.get(backend_url, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    logs = data.get("logs", [])
                    
                    if len(logs) > self.last_log_count:
                        # Find new logs
                        new_logs = logs[self.last_log_count:]
                        for log in new_logs:
                            self.root.after(0, self.add_message, log)
                        self.last_log_count = len(logs)
                    
                    self.root.after(0, lambda: self.status_label.config(
                        text="● Backend Connected", fg="#48bb78"
                    ))
                else:
                    self.root.after(0, lambda: self.status_label.config(
                        text="● Server Error", fg="#f56565"
                    ))
            except Exception:
                self.root.after(0, lambda: self.status_label.config(
                    text="● Disconnected from Backend", fg="#a0aec0"
                ))
            
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = LogMonitor(root)
    
    # Custom closure handle
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
