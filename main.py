"""
Root entrypoint for Render and cloud hosting platforms.
Allows running 'uvicorn main:app' directly from the repository root directory.
"""
import sys
import os
import importlib.util

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PathoGuard-AI-Backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

spec = importlib.util.spec_from_file_location("backend_main", os.path.join(backend_dir, "main.py"))
backend_module = importlib.util.module_from_spec(spec)
sys.modules["backend_main"] = backend_module
spec.loader.exec_module(backend_module)

app = backend_module.app
