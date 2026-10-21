"""
PathoGuard-AI — Clean Distribution Package Builder & Sanitizer
Creates a clean, production-ready source archive strictly excluding:
- .env secrets
- .venv virtual environments
- Persistent SQLite databases (*.db)
- User-uploaded demonstration documents in uploads/
- Temporary caches, logs, and OS artifacts
"""

import os
import zipfile
from pathlib import Path


EXCLUDE_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", ".pytest_cache",
    ".idea", ".vscode", "logs", ".system_generated"
}

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3",
    ".log", ".tmp", ".bak", ".swp", ".zip"
}

EXCLUDE_EXACT_FILES = {
    ".env", ".env.local", "Thumbs.db", ".DS_Store"
}


def is_excluded(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    
    # Check directory exclusions
    for part in rel_parts[:-1]:
        if part in EXCLUDE_DIRS:
            return True
            
    # Check file exclusions
    if path.name in EXCLUDE_EXACT_FILES:
        return True
        
    if path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True
        
    # Check uploads directory (only keep .gitkeep)
    if "uploads" in rel_parts and path.name != ".gitkeep":
        return True
        
    # Check data directory (only keep .gitkeep, exclude .db)
    if "data" in rel_parts and path.suffix.lower() in [".db", ".sqlite", ".sqlite3"]:
        return True
        
    return False


def build_clean_package(project_root: str, output_zip_path: str):
    root = Path(project_root).resolve()
    out_path = Path(output_zip_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    included_count = 0
    excluded_count = 0
    
    print(f"==================================================")
    print(f"PATHOGUARD-AI CLEAN DISTRIBUTION PACKAGE BUILDER")
    print(f"Root: {root}")
    print(f"Target: {out_path}")
    print(f"==================================================")
    
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in root.rglob("*"):
            if file_path.is_dir():
                continue
                
            if is_excluded(file_path, root):
                excluded_count += 1
                continue
                
            arcname = file_path.relative_to(root)
            zipf.write(file_path, arcname)
            included_count += 1
            
    print(f"[SUCCESS] Packaged {included_count} clean source files into {out_path.name}")
    print(f"[SANITIZED] Excluded {excluded_count} sensitive/binary/cache files (.env, .venv, *.db, uploads)")
    print(f"Archive size: {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    workspace_root = current_dir.parent.parent
    target_zip = workspace_root / "dist" / "PathoGuard-AI-Clean-Distribution.zip"
    build_clean_package(str(workspace_root), str(target_zip))
