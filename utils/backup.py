"""
Backup System - Daily backups with rotation
"""
import shutil
import json
from datetime import datetime
from pathlib import Path
from config.settings import settings

MAX_BACKUPS = 5
BACKUP_DIR = settings.BASE_DIR / "backups"


def create_backup():
    """Create a backup of all storage data"""
    BACKUP_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir(exist_ok=True)
    
    # Files/folders to backup
    to_backup = [
        settings.STORAGE_DIR,
        settings.BASE_DIR / "profile",
    ]
    
    for source in to_backup:
        if source.exists():
            dest = backup_path / source.name
            if source.is_dir():
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)
    
    # Create backup manifest
    manifest = {
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "contents": [str(p.name) for p in backup_path.iterdir()]
    }
    
    with open(backup_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Rotate old backups
    rotate_backups()
    
    return backup_path


def rotate_backups():
    """Keep only the last MAX_BACKUPS backups"""
    if not BACKUP_DIR.exists():
        return
    
    backups = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        key=lambda x: x.name,
        reverse=True
    )
    
    # Remove old backups
    for old_backup in backups[MAX_BACKUPS:]:
        shutil.rmtree(old_backup)


def restore_backup(backup_name: str = None):
    """Restore from a backup"""
    if not BACKUP_DIR.exists():
        return False, "No backups found"
    
    backups = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        key=lambda x: x.name,
        reverse=True
    )
    
    if not backups:
        return False, "No backups found"
    
    # Use specified or latest backup
    if backup_name:
        backup_path = BACKUP_DIR / backup_name
        if not backup_path.exists():
            return False, f"Backup {backup_name} not found"
    else:
        backup_path = backups[0]
    
    # Restore storage
    storage_backup = backup_path / "storage"
    if storage_backup.exists():
        if settings.STORAGE_DIR.exists():
            shutil.rmtree(settings.STORAGE_DIR)
        shutil.copytree(storage_backup, settings.STORAGE_DIR)
    
    # Restore profile
    profile_backup = backup_path / "profile"
    profile_dest = settings.BASE_DIR / "profile"
    if profile_backup.exists():
        if profile_dest.exists():
            shutil.rmtree(profile_dest)
        shutil.copytree(profile_backup, profile_dest)
    
    return True, f"Restored from {backup_path.name}"


def list_backups() -> list[dict]:
    """List all available backups"""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for d in sorted(BACKUP_DIR.iterdir(), key=lambda x: x.name, reverse=True):
        if d.is_dir() and d.name.startswith("backup_"):
            manifest_file = d / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file) as f:
                    manifest = json.load(f)
                backups.append({
                    "name": d.name,
                    "created_at": manifest.get("created_at"),
                    "contents": manifest.get("contents", [])
                })
            else:
                backups.append({
                    "name": d.name,
                    "created_at": None,
                    "contents": []
                })
    
    return backups


def get_backup_stats() -> dict:
    """Get backup statistics"""
    backups = list_backups()
    
    if not backups:
        return {"count": 0, "latest": None, "max": MAX_BACKUPS}
    
    return {
        "count": len(backups),
        "latest": backups[0]["created_at"] if backups else None,
        "max": MAX_BACKUPS,
        "backups": [b["name"] for b in backups]
    }
