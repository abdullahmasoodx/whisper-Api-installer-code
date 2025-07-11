import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import requests
import os
import sys
import threading

LOG_FILE = "logs.txt"

class LogViewerApp:

    VENV_DIR = "env"
    REQUIREMENTS = "requirements.txt"
    FLASK_FILE = "app.py"

    def __init__(self, root):
        self.root = root
        self.root.title("Flask API Log Viewer")
        self.root.geometry("650x550")

        # Model Selection
        control_frame = tk.Frame(root)
        control_frame.pack(pady=10)

        tk.Label(control_frame, text="Select Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(control_frame, textvariable=self.model_var)
        self.model_dropdown['values'] = ['tiny', 'base', 'small', 'medium', 'large']
        self.model_dropdown.current(0)
        self.model_dropdown.pack(side=tk.LEFT, padx=5)

        submit_btn = tk.Button(control_frame, text="Submit Model", command=self.submit_model)
        submit_btn.pack(side=tk.LEFT, padx=10)

        # Start/Stop Server Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.start_btn = tk.Button(btn_frame, text="Start Server", command=self.start_server_thread)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = tk.Button(btn_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        # Log Area
        self.log_area = ScrolledText(root, state='disabled', height=25)
        self.log_area.pack(fill='both', expand=True, padx=10, pady=10)

        self.server_process = None
        self.update_logs()

    def submit_model(self):
        model = self.model_var.get()
        try:
            response = requests.post("http://127.0.0.1:5000/set_model", json={"model": model})
            if response.ok:
                self.log_gui(f"✅ Model set to: {model}\n")
            else:
                self.log_gui(f"❌ Failed to set model. Status: {response.status_code}\n")
        except Exception as e:
            self.log_gui(f"❌ Could not set model: {e}\n")
    
    def start_server_thread(self):
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        if self.server_process is not None:
            self.log_gui("⚠️ Server is already running.\n")
            return

        self.log_gui("🔧 Checking virtual environment...\n")

        if not os.path.exists(self.VENV_DIR):
            self.log_gui("🔧 Creating virtual environment...\n")
            result = subprocess.call([sys.executable, "-m", "venv", self.VENV_DIR])
            if result != 0:
                self.log_gui("❌ Failed to create virtual environment.\n")
                return
        else:
            self.log_gui("✅ Virtual environment already exists.\n")

        # Paths
        python_path = os.path.join(self.VENV_DIR, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(self.VENV_DIR, "bin", "python")

        if not os.path.exists(python_path):
            self.log_gui(f"❌ Python executable not found in: {python_path}\n")
            return

        # Install requirements
        self.log_gui("📦 Installing requirements...\n")
        try:
            process = subprocess.Popen([python_path, "-m", "pip", "install", "-r", self.REQUIREMENTS],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       text=True)
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.log_gui(line)
            process.wait()
        except Exception as e:
            self.log_gui(f"❌ pip install failed: {e}\n")
            return

        # Start Flask app
        self.log_gui("🚀 Starting Flask server...\n")
        try:
            self.server_process = subprocess.Popen([python_path, self.FLASK_FILE])
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        except Exception as e:
            self.log_gui(f"❌ Failed to start Flask server: {e}\n")

    def stop_server(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.server_process = None
            self.log_gui("🛑 Flask server stopped.\n")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def update_logs(self):
        if not hasattr(self, 'last_log_pos'):
            self.last_log_pos = 0

        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                f.seek(self.last_log_pos)  # Go to last read position
                new_lines = f.read()
                self.last_log_pos = f.tell()  # Update current read position

                if new_lines:
                    self.log_area.config(state='normal')
                    self.log_area.insert(tk.END, new_lines)
                    self.log_area.yview(tk.END)
                    self.log_area.config(state='disabled')

        self.root.after(1000, self.update_logs)

    def log_gui(self, text):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, text)
        self.log_area.yview(tk.END)
        self.log_area.config(state='disabled')
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = LogViewerApp(root)
    root.mainloop()
