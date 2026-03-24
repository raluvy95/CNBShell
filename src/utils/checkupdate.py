import json
import os
import subprocess
from datetime import datetime
from shutil import which
from typing import List, Dict, Any

from src.utils.threads import run_in_thread 
from typing import TypedDict, List, NotRequired

class PackageUpdate(TypedDict):
    name: str
    old_version: str
    new_version: str
    raw: NotRequired[str]  # Only exists if parsing failed

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "arch-checkupdate.json")

def _get_repo_updates() -> List[str]:
    if not which("checkupdates"):
        return []
    try:
        res = subprocess.run(["checkupdates"], capture_output=True, text=True)
        return res.stdout.strip().splitlines() if res.stdout else []
    except Exception:
        return []

def _get_aur_updates() -> List[str]:
    """Internal: Fetches AUR updates."""
    if not (which("aur") and which("pacman")):
        return []
    try:
        # Using shell=True here is acceptable as the command is static
        # and we are already in a background thread.
        cmd = "pacman -Qm | aur vercmp"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.stdout.strip().splitlines() if res.stdout else []
    except Exception:
        return []

def _parse_package_line(line: str) -> PackageUpdate:
    parts = line.split()
    # Standard format: "pkgname oldver -> newver"
    if len(parts) >= 4:
        return {
            "name": parts[0],
            "old_version": parts[1],
            "new_version": parts[3]
        }
    
    # Fallback for malformed lines
    return {
        "name": "unknown",
        "old_version": "???",
        "new_version": "???",
        "raw": line
    }

@run_in_thread
def checkupdate_main(with_aur: bool = False, force: bool = False) -> str:
    """
    Exportable API: Returns a JSON string of available updates.
    """
    # 1. Cache Validation
    if not force and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data: Dict[str, Any] = json.load(f)
                last_update_str = cache_data.get("last-update", "")
                
                if last_update_str:
                    last_update = datetime.fromisoformat(last_update_str)
                    if (datetime.now().date() == last_update.date() and 
                        cache_data.get("withAUR") == with_aur):
                        return json.dumps(cache_data.get("packages", []), indent=4)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # 2. Acquisition
    updates = _get_repo_updates()
    if with_aur:
        updates.extend(_get_aur_updates())
    
    parsed_packages = [_parse_package_line(pkg) for pkg in updates]

    # 3. Storage
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    final_payload = {
        "last-update": datetime.now().isoformat(),
        "withAUR": with_aur,
        "packages": parsed_packages
    }
    
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(final_payload, f)
    except OSError:
        pass 

    return json.dumps(parsed_packages, indent=4)