import subprocess
import sys
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"


def get_python():
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def check_node():
    try:
        node_cmd = "node"
        subprocess.run([node_cmd, "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def find_npm():
    npm = "npm.cmd" if os.name == "nt" else "npm"
    try:
        subprocess.run([npm, "--version"], capture_output=True, check=True)
        return npm
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main():
    os.chdir(str(BASE_DIR))
    python = get_python()

    if not check_node():
        print("[!] Node.js not found. Please install Node.js >= 18")
        input("Press Enter to exit...")
        return

    npm = find_npm()
    if not npm:
        print("[!] npm not found. Please install Node.js >= 18")
        input("Press Enter to exit...")
        return

    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("[*] Installing frontend dependencies...")
        subprocess.run([npm, "install"], cwd=str(FRONTEND_DIR), check=True)

    print(f"[*] Python: {python}")
    print("[*] Starting backend on port 8000...")
    backend = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(BASE_DIR),
    )

    print("[*] Starting frontend on port 5173...")
    frontend = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    print()
    print("=" * 50)
    print("  Uni-TTS 已启动")
    print("  前端: http://localhost:5173")
    print("  后端: http://localhost:8000")
    print("  按 Ctrl+C 退出")
    print("=" * 50)
    print()

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print(f"[!] Backend exited (code {backend.returncode})")
                frontend.terminate()
                break
            if frontend.poll() is not None:
                print(f"[!] Frontend exited (code {frontend.returncode})")
                backend.terminate()
                break
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        for p in (backend, frontend):
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == "__main__":
    main()
