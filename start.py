import subprocess
import sys
import os
import time
import webbrowser
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


def git_pull():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[*] Git not found, skipping update check")
        return False

    print("[*] Checking for updates...")
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(BASE_DIR), capture_output=True, text=True
        )
        if result.returncode != 0:
            return False

        fetch_proc = subprocess.Popen(
            ["git", "fetch", "origin"],
            cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        fetch_out = fetch_proc.communicate()[0]
        if fetch_proc.returncode != 0:
            print("[!] Failed to fetch updates")
            return False

        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BASE_DIR), capture_output=True, text=True
        ).stdout.strip()

        remote = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(BASE_DIR), capture_output=True, text=True
        ).stdout.strip()

        if not remote or local == remote:
            print("[*] Already up to date")
            return False

        log_result = subprocess.run(
            ["git", "log", "--format=%h %s", f"{local}..{remote}"],
            cwd=str(BASE_DIR), capture_output=True, text=True
        )
        log = log_result.stdout.strip()
        if not log:
            print("[*] Already up to date")
            return False

        commits = log.splitlines()
        print(f"\n[*] Found {len(commits)} new commit(s):")
        print("-" * 50)
        for line in commits:
            print(f"  {line}")
        print("-" * 50)

        answer = input("\n[*] Update now? (y/N): ").strip().lower()
        if answer != 'y':
            print("[*] Skipping update")
            return False

        print("\n[*] Pulling updates...")
        pull_proc = subprocess.Popen(
            ["git", "pull", "origin", "main"],
            cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in pull_proc.stdout:
            line = line.rstrip()
            if line:
                print(f"    {line}")
        pull_proc.wait()

        if pull_proc.returncode == 0:
            print("[*] Update completed")
            return True
        else:
            print("[!] Update failed")
            return False
    except subprocess.TimeoutExpired:
        print("[!] Update check timed out")
        return False
    except KeyboardInterrupt:
        print("\n[*] Skipping update")
        return False
    except Exception as e:
        print(f"[!] Update check failed: {e}")
        return False


def main():
    os.chdir(str(BASE_DIR))
    python = get_python()

    updated = git_pull()

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
    if not node_modules.exists() or updated:
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

    time.sleep(2)
    webbrowser.open("http://localhost:5173")

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
