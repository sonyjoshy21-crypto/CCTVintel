import tkinter as tk
from tkinter import scrolledtext, ttk
import requests
import time
import threading

class AdvancedMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTVIntel - Advanced AI & System Monitor")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0f172a")

        # --- Top Header & Metrics ---
        header_frame = tk.Frame(root, bg="#1e293b", pady=15, padx=20)
        header_frame.pack(fill='x')

        title_label = tk.Label(
            header_frame, text="ANALYSIS DIAGNOSTICS", 
            fg="#22d3ee", bg="#1e293b", 
            font=("Consolas", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky='w')

        self.matches_label = tk.Label(
            header_frame, text="MATCHES: 0", 
            fg="#fbbf24", bg="#1e293b", 
            font=("Consolas", 14, "bold"), padx=30
        )
        self.matches_label.grid(row=0, column=1)

        self.fps_label = tk.Label(
            header_frame, text="ENGINE: Idle", 
            fg="#94a3b8", bg="#1e293b", 
            font=("Consolas", 10), padx=20
        )
        self.fps_label.grid(row=0, column=2, sticky='e')

        # --- Progress Bar ---
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=20, pady=5)

        # --- Main Log Area (Paned) ---
        paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, bg="#0f172a", borderwidth=0, sashwidth=4)
        paned.pack(expand=True, fill='both', padx=10, pady=10)

        # AI BRAIN COLUMN
        ai_frame = tk.LabelFrame(paned, text=" AI BRAIN LOGIC (CLIP / LLM) ", 
                                fg="#818cf8", bg="#0f172a", font=("Consolas", 10, "bold"), 
                                padx=5, pady=5, borderwidth=1)
        self.ai_area = scrolledtext.ScrolledText(
            ai_frame, bg="#020617", fg="#c7d2fe", 
            font=("Consolas", 9), borderwidth=0
        )
        self.ai_area.pack(expand=True, fill='both')
        paned.add(ai_frame, width=500)

        # SYSTEM ENGINE COLUMN
        sys_frame = tk.LabelFrame(paned, text=" SYSTEM ENGINE (YOLO / FFMPEG) ", 
                                 fg="#2dd4bf", bg="#0f172a", font=("Consolas", 10, "bold"), 
                                 padx=5, pady=5, borderwidth=1)
        self.sys_area = scrolledtext.ScrolledText(
            sys_frame, bg="#020617", fg="#ccfbf1", 
            font=("Consolas", 9), borderwidth=0
        )
        self.sys_area.pack(expand=True, fill='both')
        paned.add(sys_frame, width=500)

        # --- Status Bar ---
        self.status_bar = tk.Label(
            root, text="Waiting for backend...", 
            fg="#94a3b8", bg="#0f172a", 
            font=("Consolas", 9), pady=5
        )
        self.status_bar.pack()

        self.last_ai_count = 0
        self.last_sys_count = 0
        self.running = True
        
        # Start polling thread
        self.poll_thread = threading.Thread(target=self.poll_logs, daemon=True)
        self.poll_thread.start()

    def add_log(self, area, message, is_error=False):
        color = "#f87171" if is_error else None
        area.insert(tk.END, message + "\n")
        area.see(tk.END)

    def poll_logs(self):
        backend_url = "http://127.0.0.1:5000/api/logs"
        while self.running:
            try:
                response = requests.get(backend_url, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    
                    # 1. Update Metrics
                    metrics = data.get("metrics", {})
                    self.progress_var.set(metrics.get("percent", 0))
                    self.matches_label.config(text=f"MATCHES: {metrics.get('matches', 0)}")
                    self.fps_label.config(text=f"STAGE: {metrics.get('stage', 'Idle')}")
                    
                    # 2. Update AI Logs
                    ai_list = data.get("ai_logs", [])
                    if len(ai_list) < self.last_ai_count:
                        # BACKEND RESET DETECTED
                        self.root.after(0, lambda: self.ai_area.delete('1.0', tk.END))
                        self.last_ai_count = 0
                        
                    if len(ai_list) > self.last_ai_count:
                        new_ai = ai_list[self.last_ai_count:]
                        for msg in new_ai:
                            self.root.after(0, lambda m=msg: self.add_log(self.ai_area, m))
                        self.last_ai_count = len(ai_list)
                        
                    # 3. Update System Logs
                    sys_list = data.get("sys_logs", [])
                    if len(sys_list) < self.last_sys_count:
                        # BACKEND RESET DETECTED
                        self.root.after(0, lambda: self.sys_area.delete('1.0', tk.END))
                        self.last_sys_count = 0

                    if len(sys_list) > self.last_sys_count:
                        new_sys = sys_list[self.last_sys_count:]
                        for msg in new_sys:
                            is_err = "!! ERROR !!" in msg or "CRITICAL FAILURE" in msg
                            self.root.after(0, lambda m=msg, e=is_err: self.add_log(self.sys_area, m, is_error=e))
                        self.last_sys_count = len(sys_list)
                    
                    self.status_bar.config(text="● CONNECTED", fg="#4ade80")
                else:
                    self.status_bar.config(text="● SERVER ERROR", fg="#f87171")
            except Exception:
                self.status_bar.config(text="● DISCONNECTED (CHECK TERMINAL)", fg="#64748b")
            
            time.sleep(1)

if __name__ == "__main__":
    # Apply some styling to the progress bar
    style_root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Horizontal.TProgressbar", foreground='#22d3ee', background='#22d3ee', thickness=10)
    
    app = AdvancedMonitor(style_root)
    
    def on_closing():
        app.running = False
        style_root.destroy()
        
    style_root.protocol("WM_DELETE_WINDOW", on_closing)
    style_root.mainloop()
