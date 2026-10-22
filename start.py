"""
PathoGuard-AI Production Web Server Launcher for Render & Cloud Platforms
Reads PORT from environment safely and launches Uvicorn.
"""
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PathoGuard-AI-Backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import uvicorn
    from main import app
except Exception as e:
    import traceback
    print(f"[FATAL] Failed to import application: {e}", file=sys.stderr, flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    port_env = os.environ.get("PORT", "10000")
    try:
        port = int(port_env)
    except (ValueError, TypeError):
        port = 10000

    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[PathoGuard Startup] Launching production server on {host}:{port} ...", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True)
