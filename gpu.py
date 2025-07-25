import platform
import psutil
import torch
import GPUtil
import subprocess
import sys

def list_cpus():
    print("🧠 CPU Info")
    print(f"Processor: {platform.processor()}")
    print(f"Physical cores: {psutil.cpu_count(logical=False)}")
    print(f"Logical cores: {psutil.cpu_count(logical=True)}\n")

def list_gpus():


    # Try integrated GPU info (Windows-only)
    if sys.platform.startswith("win"):
        try:
            print("Integrated GPUs / Display Adapters:")
            result = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")[1:]  # skip header
            for idx, name in enumerate(lines):
                print(f"  GPU {idx}: {name.strip()}")
        except Exception as e:
            print("Unable to fetch integrated GPU info:", str(e))
    else:
        print("Integrated GPU listing is only implemented for Windows.")

    print("\n")

def list_cuda_devices():
    
    print("-----------------------------------------")
    print("⚡ CUDA-Capable GPUs")
    
    if torch.cuda.is_available():
        print("\nAvailable Cuda Supported GPUs are: ", torch.cuda.device_count())
        for i in range(torch.cuda.device_count()):
            print(f"\nCUDA GPU {i}: {torch.cuda.get_device_name(i)}")
            print("🎮 GPU Info")

            # NVIDIA GPUs via GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                for gpu in gpus:
                    print(f"NVIDIA GPU {gpu.id}: {gpu.name}")
                    print(f"  Memory: {gpu.memoryUsed} MB / {gpu.memoryTotal} MB")
                    print(f"  Load: {gpu.load * 100:.1f}%")
                    print(f"  Temperature: {gpu.temperature} °C\n")
            else:
                print("No NVIDIA GPU found (GPUtil).\n")
    
    else:
        print("No CUDA-capable GPUs found.")
        
     

# Run all
list_cpus()
list_gpus()
list_cuda_devices()
