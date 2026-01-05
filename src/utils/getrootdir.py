from pathlib import Path

def get_project_root() -> Path:
    current_path = Path(__file__).resolve()
    # Traverse up the directory tree until we find a marker file
    for parent in [current_path] + list(current_path.parents):
        if (parent / ".git").exists() or (parent / "requirements.txt").exists():
            return parent
    return current_path.parent