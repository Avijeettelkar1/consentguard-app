"""
One-command local dev runner.

Usage:
    python run_local.py

What it does:
    1. Serves test_site/ on http://localhost:3000
    2. Starts FastAPI backend on http://localhost:8000 (LOCAL_PLAYWRIGHT mode)
    3. Prints instructions for opening the frontend

Stop with Ctrl+C.
"""
import os
import sys
import subprocess
import threading
import http.server
import socketserver
import time

TEST_SITE_PORT = 3000
BACKEND_PORT = 8000
TEST_SITE_DIR = os.path.join(os.path.dirname(__file__), "test_site")
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")


def serve_test_site():
    os.chdir(TEST_SITE_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None  # silence request logs
    with socketserver.TCPServer(("", TEST_SITE_PORT), handler) as httpd:
        print(f"  [test site]  http://localhost:{TEST_SITE_PORT}")
        httpd.serve_forever()


def serve_backend():
    env = os.environ.copy()
    env["LOCAL_PLAYWRIGHT"] = "true"
    env["MOCK"] = "false"
    # load .env if it exists
    env_file = os.path.join(BACKEND_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    subprocess.run(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", f"--port={BACKEND_PORT}"],
        cwd=BACKEND_DIR,
        env=env,
    )


if __name__ == "__main__":
    print("\nConsentGuard — Local Dev Server")
    print("=" * 40)

    t = threading.Thread(target=serve_test_site, daemon=True)
    t.start()
    time.sleep(0.5)

    print(f"  [backend]    http://localhost:{BACKEND_PORT}")
    print(f"  [frontend]   open frontend/index.html in your browser")
    print(f"\n  Test URL to scan: http://localhost:{TEST_SITE_PORT}")
    print(f"  Health check:     http://localhost:{BACKEND_PORT}/health")
    print("\n  Press Ctrl+C to stop.\n")

    serve_backend()
