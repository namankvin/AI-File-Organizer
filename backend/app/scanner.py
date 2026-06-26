from pathlib import Path
from datetime import datetime

import hashlib

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".html",
    ".css",
}

def is_probably_text_file(path: Path, sample_size: int = 4096) -> bool:
    try:
        with path.open("rb") as file:
            sample = file.read(sample_size)
    except OSError:
        return False

    if not sample:
        return False

    if b"\x00" in sample:
        return False
    
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def scan_folder(folder_path: str) -> list[dict]:
    root = Path(folder_path)
    if not root.exists():
        return []
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append({
            "path" : str(path),
            "name" : path.name,
            "extension" : path.suffix or None,
            "size_bytes" : stat.st_size,
            "modified_at" : datetime.fromtimestamp(stat.st_mtime),
            "content_hash" : get_content_hash(path),
            "text_preview" : get_text_preview(path),
        })
    return files

def get_content_hash(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            
            if chunk == b"":
                break

            hasher.update(chunk)
    
    return hasher.hexdigest()

def get_text_preview(path: Path, max_chars: int = 1000) -> str | None:
    extension = path.suffix.lower()

    if extension not in TEXT_EXTENSIONS and not is_probably_text_file(path):
        return None

    try:
        text = path.read_text(encoding = "utf-8", errors = "ignore")
    except OSError:
        return None

    return text[:max_chars]