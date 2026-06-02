import socket
import subprocess
import time
from gui.window import run_app

def ensure_ollama_running():
    """Check if Ollama server is running on port 11434. If not, auto-start it silently."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", 11434))
        s.close()
        print("[Ollama] Ollama server is already running.")
        return True
    except Exception:
        pass

    try:
        print("[Ollama] Ollama server is not running. Starting it now in the background...")
        # 0x08000000 is CREATE_NO_WINDOW flag on Windows to run it silently
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        time.sleep(3.5)  # Wait for server to bind to port
        return True
    except Exception as e:
        print(f"[Ollama] Failed to auto-start Ollama: {e}")
        return False

if __name__ == "__main__":
    ensure_ollama_running()
    run_app()
