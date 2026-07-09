from fastapi import FastAPI, HTTPException
from pathlib import Path
from datetime import datetime

from app import models
from app.config import APP_NAME, DATABASE_URL
from app.database import Base, engine, SessionLocal
from app.scanner import scan_folder
from app.models import FileRecord, MoveSuggestion
from app.embeddings import EMBEDDING_MODEL_NAME, build_embedding_text, generate_embedding, serialize_embedding, deserialize_embedding, cosine_similarity
from app.planner import create_move_plan_for_file

app = FastAPI(title = APP_NAME)

Base.metadata.create_all(bind = engine)

@app.get("/health")
def health_check() :
    return {
        "status" : "ok",
        "app" : APP_NAME,
        "database_url" : DATABASE_URL,
    }

@app.post("/scan")
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
    # Always close the DB session, even if scanning or database writes fail.
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
    # Always close the DB session, even if scanning or database writes fail.
    finally:
        db.close()
    
@app.post("/embed")
def embed_files():
    db = SessionLocal()

    try:
        files = db.query(FileRecord).filter(FileRecord.embedding.is_(None)).all()
        embedded_count = 0
        skipped_count = 0

        for file in files:
            text = build_embedding_text(file)
            if (text != ""):
                embedding = generate_embedding(text)
                file.embedding = serialize_embedding(embedding) # Store the vector as JSON text because SQLite does not store Python lists directly.
                file.embedding_model = EMBEDDING_MODEL_NAME
                file.embedding_updated_at = datetime.now()
                embedded_count += 1
            else:
                skipped_count += 1
        
        db.commit()

        return {
            "embedded_count": embedded_count,
            "skipped_count": skipped_count,
            "model": EMBEDDING_MODEL_NAME
        }
    finally:
        db.close()

def get_semantic_search_results(db, query: str, limit: int) -> list[dict]:
    query_embedding = generate_embedding(query)
    files = db.query(FileRecord).filter(FileRecord.embedding.isnot(None)).all()

    results = []

    for file in files:
        file_embedding = deserialize_embedding(file.embedding)
        score = cosine_similarity(query_embedding, file_embedding)

        results.append({
            "id": file.id,
            "name": file.name,
            "path": file.path,
            "extension": file.extension,
            "score": score,
            "text_preview": file.text_preview,
        })

    # Highest cosine scores are the most semantically similar matches.
    results.sort(key=lambda item: item["score"], reverse=True)

    return results[:limit]

@app.get("/search")
def search_files(query: str, limit: int = 5):
    db = SessionLocal()

    try:
        results = get_semantic_search_results(db, query, limit)

        return {
            "query": query,
            "count": len(results),
            "results": results
        }
    finally:
        db.close()

@app.get("/rag/answer")
def rag_answer(query: str, limit: int = 3, min_score: float = 0.25):
    db = SessionLocal()
    try:
        top_results = get_semantic_search_results(db, query, limit)
        filtered_results = []
        for result in top_results:
            if result["score"] >= min_score:
                filtered_results.append(result)
        top_results = filtered_results

        if not top_results:
            answer = "I could not find any relevant files."
        else:
            file_names = []

            for item in top_results:
                file_names.append(item["name"])
            answer = f"I found {len(top_results)} relevant file(s): " + ", ".join(file_names)

        return {
            "query": query,
            "answer": answer,
            "relevant_files": top_results
        }
    finally:
        db.close()

@app.post("/plan")
def create_plan(query: str | None = None, target_folder: str | None = None, limit: int = 10, min_score: float = 0.50):
    db = SessionLocal()
    try:
        # Rebuild the current pending plan so the preview reflects the latest scan.
        db.query(MoveSuggestion).filter(MoveSuggestion.status == "pending").delete()

        if query and target_folder:
            # Command mode plans moves into a user-provided target folder, but does not move files yet.
            search_results = get_semantic_search_results(db, query, limit)
            suggestions = []

            for result in search_results:
                if result["score"] < min_score:
                    continue
                source_path = result["path"]
                file_name = Path(source_path).name
                target_path = str(Path(target_folder) / file_name)

                suggestion_data = {
                    "file_id": result["id"],
                    "source_path": source_path,
                    "target_path": target_path,
                    "category": Path(target_folder).name,
                    "confidence": result["score"],
                    "reason": f"Matched command query '{query}' using semantic similarity",
                }

                suggestions.append(suggestion_data)
                suggestion = MoveSuggestion(**suggestion_data)
                db.add(suggestion)

            db.commit()

            return {
                "mode" : "command",
                "query" : query,
                "target_folder" : target_folder,
                "suggestion_count" : len(suggestions),
                "suggestions" : suggestions
            }

        files = db.query(FileRecord).all()
        suggestions = []

        for file in files:
            suggestion_data = create_move_plan_for_file(file)
            suggestions.append(suggestion_data)
            suggestion = MoveSuggestion(**suggestion_data)
            db.add(suggestion)
        
        db.commit()
        
        return {
            "mode": "auto",
            "suggestion_count": len(suggestions),
            "suggestions": suggestions
        }
    finally:
        db.close()