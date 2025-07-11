import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
import requests
import os
import sys
import threading
import ctypes
import shutil
import winreg

LOG_FILE = "logs.txt"

class LogViewerApp:

    VENV_DIR = "env"
    REQUIREMENTS = "requirements.txt"
    FLASK_FILE = "data/app.exe"

    


    def __init__(self, root):
        os.chdir(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__))
        # marker = os.path.join(os.path.dirname(__file__), "post_install_done.flag")
        # if not os.path.exists(marker):
        #     self.run_post_install()
        #     with open(marker, "w") as f:
        #         f.write("done")
        # Reset log file on start
        if os.path.exists(LOG_FILE):
            try:
                os.remove(LOG_FILE)
                #self.log_gui("🧹 Previous log file deleted.\n")
            except Exception as e:
                print(f"❌ Failed to delete old log file: {e}\n")
        # Create new empty log file
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")  # Create empty file
            #self.log_gui("📄 New log file created.\n")
        except Exception as e:
            #self.log_gui(f"❌ Failed to create new log file: {e}\n")
            print(f"❌ Failed to create new log file: {e}\n")
       
        self.install_ffmpeg()


        self.root = root
        self.root.title("Flask API Log Viewer")
        self.root.geometry("650x550")

        # Model Selection
        control_frame = tk.Frame(root)
        control_frame.pack(pady=10)

        tk.Label(control_frame, text="Select Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(control_frame, textvariable=self.model_var)

        self.model_dropdown['values'] = ["large-v3-turbo"]
       # self.model_dropdown['values'] = ["large-v3-turbo",'tiny', 'tiny.en', 'base', 'base.en', 'small','small.en',"medium","medium.en","large","large-v1","large-v2","large-v3"]

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

        self.reinstall_btn = tk.Button(btn_frame, text="Reinstall Setup", command=self.reinstall_setup)
        self.reinstall_btn.pack(side=tk.LEFT, padx=10)

        # Log Area
        self.log_area = ScrolledText(root, state='disabled', height=25)
        self.log_area.pack(fill='both', expand=True, padx=10, pady=10)

        self.server_process = None
        self.update_logs()

        # Auto install on first run if env missing
        if not os.path.exists(self.VENV_DIR):
            self.log_gui("🔧 Virtual environment not found. Setting up...\n")
            threading.Thread(target=self.setup_virtualenv, daemon=True).start()



    # def run_post_install():
    #     exe_dir = os.path.dirname(os.path.abspath(__file__))
    #     bat_file = os.path.join(exe_dir, "installer_assets/post_install.bat")

    #     if os.path.exists(bat_file):
    #         try:
    #             subprocess.call(["cmd", "/c", bat_file])
    #             print("✅ post_install.bat executed.")
    #         except Exception as e:
    #             print(f"❌ Failed to run post_install.bat: {e}")
    #     else:
    #         print("⚠️ post_install.bat not found.")

    # # Optional: Only run once (create a marker file after)
   



    def install_ffmpeg(self):
        FFMPEG_SOURCE = os.path.abspath("ffmpeg")  # Should be a local folder next to your script
        FFMPEG_DEST = r"C:\ffmpeg"
        FFMPEG_BIN = os.path.join(FFMPEG_DEST, "bin")

       # self.log_gui("🔍 Installing FFmpeg...\n")

        # Step 1: Copy to C:\ffmpeg if not already
        if not os.path.exists(FFMPEG_DEST):
            try:
                shutil.copytree(FFMPEG_SOURCE, FFMPEG_DEST)
                #self.log_gui("✅ FFmpeg copied to C:\\ffmpeg\n")
            except Exception as e:
               # self.log_gui(f"❌ Failed to copy FFmpeg: {e}\n")
                return
        

        # Step 2: Add FFmpeg bin to user PATH if not already
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                try:
                    current_path, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current_path = ""

                if FFMPEG_BIN not in current_path:
                    new_path = current_path + ";" + FFMPEG_BIN if current_path else FFMPEG_BIN
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                   # self.log_gui("✅ FFmpeg path added to user PATH.\n🔁 Please restart your system or re-login.\n")
               
        except Exception as e:
            print("dsd")
            #self.log_gui(f"❌ Failed to modify PATH: {e}\n")



    def start_Systemservice(service_name):
        result = subprocess.run(["net", "start", service_name], capture_output=True, text=True, shell=True)
           


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
        
        os.system("taskkill /f /im app.py >nul 2>&1")
        os.system("taskkill /f /im app.py >nul 2>&1")

        if self.server_process is not None:
            self.log_gui("⚠️ Server is already running.\n")
            return

        self.log_gui("🔧 Checking virtual environment...\n")

        if not os.path.exists(self.VENV_DIR):
            self.log_gui("🔧 Creating virtual environment...\n")
            self.setup_virtualenv()
            return
        else:
            self.log_gui("✅ Virtual environment already exists. Skipping install.\n")
        
        threading.Thread(target=self.reinstall_setup, daemon=True).start()
        # Start Flask app
        self.log_gui("🚀 Starting Flask server...\n")
        # Path to the Python inside your venv
        app_py_path = os.path.abspath("models/app/app.exe")

        try:
            self.server_process = subprocess.Popen([app_py_path], creationflags=subprocess.CREATE_NO_WINDOW)
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        except Exception as e:
            self.log_gui(f"❌ Failed to start Flask server: {e}\n")

    def stop_server(self):
        os.system("taskkill /f /im app.exe >nul 2>&1")
        os.system("taskkill /f /im app.exe >nul 2>&1")
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.server_process = None
            self.log_gui("🛑 Flask server stopped.\n")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)



    def setup_virtualenv(self):
        result = subprocess.call(["py", "-3.11", "-m", "venv", self.VENV_DIR])

        #result = subprocess.call([sys.executable, "-m", "venv", self.VENV_DIR])
        if result != 0:
            self.log_gui("❌ Failed to create virtual environment.\n")
            return

        python_path = os.path.join(self.VENV_DIR, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(self.VENV_DIR, "bin", "python")

        if os.path.exists(python_path):
            self.install_requirements(python_path)
        else:
            self.log_gui(f"❌ Python executable not found in: {python_path}\n")

    def install_requirements(self, python_path):
        self.log_gui("📦 Installing requirements...\n")
        try:
            process = subprocess.Popen(
                [python_path, "-m", "pip", "install", "-r", self.REQUIREMENTS],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )

            def read_output():
                for line in iter(process.stdout.readline, ''):
                    self.log_gui(line)
                process.stdout.close()
                process.wait()
                if process.returncode == 0:
                    self.log_gui("✅ Requirements installed successfully.\n")
                else:
                    self.log_gui("❌ Requirements installation failed.\n")

            threading.Thread(target=read_output, daemon=True).start()
            
        except Exception as e:
            self.log_gui(f"❌ pip install failed: {e}\n")





    def reinstall_setup(self):
        python_path = os.path.join(self.VENV_DIR, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(self.VENV_DIR, "bin", "python")
        if not os.path.exists(python_path):
            self.log_gui("❌ Python executable not found. Create the environment first.\n")
            return
        self.install_requirements(python_path)

    def update_logs(self):
        if not hasattr(self, 'last_log_pos'):
            self.last_log_pos = 0

        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                f.seek(self.last_log_pos)
                new_lines = f.read()
                self.last_log_pos = f.tell()

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
        #self.root.update_idletasks()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Relaunch as admin if not already
if not is_admin():
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", pythonw, " ".join(sys.argv), None, 1
    )
    sys.exit()

    
if __name__ == "__main__":
    
    root = tk.Tk()
    app = LogViewerApp(root)
    root.mainloop()
