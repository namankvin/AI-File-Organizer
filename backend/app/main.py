from fastapi import FastAPI, HTTPException
from pathlib import Path

from app import models
from app.config import APP_NAME, DATABASE_URL
from app.database import Base, engine, SessionLocal
from app.scanner import scan_folder
from app.models import FileRecord

app = FastAPI(title = APP_NAME)

Base.metadata.create_all(bind = engine)

@app.get("/health")
def health_check() :
    return {
        "status" : "ok",
        "app" : APP_NAME,
        "database_url" : DATABASE_URL,
    }

@app.get("/scan")
def scan(folder_path: str):
    root = Path(folder_path)

    if not root.exists():
        raise HTTPException(status_code = 404, detail = "Folder does not exist!")
    
    if not root.is_dir():
        raise HTTPException(status_code = 400, detail = "Path is not a folder")

    files = scan_folder(folder_path)

    db = SessionLocal()

    try:
        created_count = 0
        updated_count = 0

        for file_data in files:
            existing_file = db.query(FileRecord).filter(FileRecord.path == file_data["path"]).first()

            if existing_file:
                existing_file.name = file_data["name"]
                existing_file.extension = file_data["extension"]
                existing_file.size_bytes = file_data["size_bytes"]
                existing_file.modified_at = file_data["modified_at"]
                existing_file.content_hash = file_data["content_hash"]
                existing_file.text_preview = file_data["text_preview"]
                updated_count += 1
            else:
                file_record = FileRecord(**file_data)
                db.add(file_record)
                created_count += 1
                
        db.commit()

        return {
            "folder_path": folder_path,
            "scanned_count": len(files),
            "created_count": created_count,
            "updated_count": updated_count,
        }

    finally:
        db.close()

@app.get("/files")
def get_files():
    db = SessionLocal()

    try:
        result = []

        files = db.query(FileRecord).all()

        for file in files:
            result.append(
                {
                    "id": file.id,
                    "path": file.path,
                    "name": file.name,
                    "extension": file.extension,
                    "size_bytes": file.size_bytes,
                    "modified_at": file.modified_at,
                    "content_hash": file.content_hash,
                    "text_preview": file.text_preview,
                    "created_at": file.created_at,
                    "updated_at": file.updated_at,
                }
            )

        return {
            "count" : len(result),
            "files" : result,
        }

    finally:
        db.close()