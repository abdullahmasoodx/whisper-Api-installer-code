from cx_Freeze import setup, Executable
import os
import sys

# Application metadata
app_name = "Whisper API GUI"
version = "1.0"
description = "A Whisper transcription API with GUI"
base = "Win32GUI" if sys.platform == "win32" else None

# List of folders/files to include
include_files = [
    ("ffmpeg", "ffmpeg"),
    ("models", "models"),
    ("requirements.txt", "requirements.txt"),
    ("WhisperApi.exe", "WhisperApi.exe")  # Your bundled Flask app
]

build_exe_options = {
    "packages": ["os", "tkinter", "requests", "shutil", "threading", "subprocess", "ctypes"],
    "include_files": include_files,
    "zip_include_packages": [],
    "zip_exclude_packages": []
}

# Setup
setup(
    name=app_name,
    version=version,
    description=description,
    options={"build_exe": build_exe_options},
    executables=[Executable("gui.py", base=base, target_name="WhisperApi.exe")],
)
