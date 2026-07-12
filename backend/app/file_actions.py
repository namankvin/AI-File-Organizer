from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOTS = [
  (PROJECT_ROOT / "sample_files").resolve(),
]

def is_path_allowed(path: Path) -> bool:
  resolved_path = path.resolve() # useful in checking symbolic links
  
  for root in ALLOWED_ROOTS:
    if resolved_path == root or root in resolved_path.parents:
      return True
      
  return False

def get_safe_target_path(target_path: str) -> Path:
    target = Path(target_path)

    if not target.exists():
        return target

    parent = target.parent
    stem = target.stem
    suffix = target.suffix

    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"

        if not candidate.exists():
            return candidate
        
        counter += 1

def move_file(source_path: str, target_path: str) -> str:
    source = Path(source_path)
    
    if not source.exists():
      raise FileNotFoundError("Source file does not exist")
    
    if not source.is_file():
      raise ValueError("Source path is not a file")
    
    safe_target = get_safe_target_path(target_path)
    
    if not is_path_allowed(source):
      raise ValueError("Source path is outside allowed roots")
    if not is_path_allowed(safe_target):
      raise ValueError("Target path is outside allowed roots")

    safe_target.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(source), str(safe_target))

    return str(safe_target)
