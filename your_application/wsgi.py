"""
Fallback WSGI/ASGI entrypoint for Render default placeholder command.
"""
import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from start import app as application  # noqa: F401

