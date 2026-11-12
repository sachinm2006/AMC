# -*- coding: utf-8 -*-
"""
Localhost Runner for Delhi DISCOM Peak-Aware Load Forecasting & Procurement Copilot
Starts FastAPI Backend (http://localhost:8000) and Vite React Frontend (http://localhost:5173).
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

def run_backend(port: int = 8000):
    print(f"\n[BACKEND] Starting FastAPI server on http://localhost:{port} (API docs: http://localhost:{port}/docs)...")
    cmd = [
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ]
    return subprocess.Popen(cmd, cwd=str(REPO_ROOT))

def run_frontend(port: int = 5173):
    frontend_dir = REPO_ROOT / "frontend"
    print(f"\n[FRONTEND] Starting Vite development server on http://localhost:{port}...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    cmd = [npm_cmd, "run", "dev", "--", "--port", str(port)]
    return subprocess.Popen(cmd, cwd=str(frontend_dir))

def main():
    parser = argparse.ArgumentParser(description="Run Delhi DISCOM Copilot on localhost.")
    parser.add_argument("--backend-only", action="store_true", help="Start only FastAPI backend")
    parser.add_argument("--frontend-only", action="store_true", help="Start only Vite frontend")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Frontend port (default: 5173)")
    args = parser.parse_args()

    procs = []
    try:
        if not args.frontend_only:
            p_back = run_backend(port=args.backend_port)
            procs.append(p_back)

        if not args.backend_only:
            time.sleep(1)
            p_front = run_frontend(port=args.frontend_port)
            procs.append(p_front)

        print("\n" + "=" * 70)
        print("  DELHI DISCOM PROCUREMENT COPILOT - LOCALHOST IS LIVE!")
        if not args.frontend_only:
            print(f"  • FastAPI Backend:    http://localhost:{args.backend_port}")
            print(f"  • Swagger API Docs:   http://localhost:{args.backend_port}/docs")
        if not args.backend_only:
            print(f"  • React Frontend UI:  http://localhost:{args.frontend_port}")
        print("=" * 70)
        print("Press Ctrl+C to terminate both servers.\n")

        for p in procs:
            p.wait()

    except KeyboardInterrupt:
        print("\nShutting down servers...")
        for p in procs:
            p.terminate()

if __name__ == "__main__":
    main()
