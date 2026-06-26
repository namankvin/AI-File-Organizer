from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "organizer.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
APP_NAME = "AI FILE ORGANIZER"