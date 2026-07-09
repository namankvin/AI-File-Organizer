from pathlib import Path
from app.embeddings import cosine_similarity, deserialize_embedding, generate_embedding

CATEGORY_TARGETS = {
    "Resumes": "../sample_files/Documents/Resumes",
    "Finance": "../sample_files/Documents/Finance",
    "Software_Engineering": "../sample_files/Documents/Software_Engineering",
    "Study_Notes": "../sample_files/Documents/Study_Notes",
    "Screenshots": "../sample_files/Documents/Screenshots",
    "Review": "../sample_files/Documents/Review",
    "Operating_Systems": "../sample_files/Documents/Operating_Systems",
}

# Day 3 uses sample folders as safe planning targets; Day 4 will apply moves.
CATEGORY_KEYWORDS = {
    "Resumes": ["resume", "cv", "curriculum vitae"],
    "Finance": ["invoice", "bank", "statement", "receipt", "payment"],
    "Software_Engineering": ["software engineering","requirements engineering","uml","software design","testing","maintenance","agile",],
    "Operating_Systems": ["operating system", "operating systems", "process scheduling", "memory management","paging", "deadlocks"],
    "Study_Notes": ["dsa", "notes", "arrays", "graphs", "recursion", "dynamic programming"],
    "Screenshots": ["screenshot", "screen shot"],
}

CATEGORY_DESCRIPTIONS = {
    "Resumes": "resume cv curriculum vitae job application internship candidate profile",
    "Finance": "invoice bank statement receipt payment transaction finance money",
    "Software_Engineering": "software engineering requirements uml design testing agile maintenance course notes",
    "Study_Notes": "study notes dsa algorithms arrays graphs recursion dynamic programming exam preparation",
    "Screenshots": "screenshot image screen capture picture png jpg",
}

CATEGORY_EMBEDDINGS = {}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def build_file_text(file_record) -> str:
    parts = [
        file_record.name or "",
        file_record.extension or "",
        file_record.text_preview or ""
    ]

    return " ".join(parts).lower()

def build_target_path(file_record, category: str) -> str:
    target_folder = CATEGORY_TARGETS[category]
    return str(Path(target_folder) / file_record.name)

def classify_with_rules(file_record) -> tuple[str, float, str]:
    file_text = build_file_text(file_record)
    extension = (file_record.extension or "").lower()

    if extension in IMAGE_EXTENSIONS or "screenshot" in file_text or "screen shot" in file_text:
        return ("Screenshots", 0.95, "Matched screenshot/image rule")
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in file_text:
                return (category, 0.85, f"Matched keyword '{keyword}'")
    
    return ("Review", 0.30, "No strong rule matched")

def create_move_plan_for_file(file_record) -> dict:
    category, confidence, reason = classify_with_rules(file_record)

    if category == "Review":
        category, confidence, reason = classify_with_semantics(file_record)

    target_path = build_target_path(file_record, category)

    return {
        "file_id": file_record.id,
        "source_path": file_record.path,
        "target_path": target_path,
        "category": category,
        "confidence": confidence,
        "reason": reason,
    }

def get_category_embedding(category: str) -> list[float]:
    if category not in CATEGORY_EMBEDDINGS:
        description = CATEGORY_DESCRIPTIONS[category]
        CATEGORY_EMBEDDINGS[category] = generate_embedding(description)

    return CATEGORY_EMBEDDINGS[category]

def get_file_embedding(file_record) -> list[float] | None:
    if file_record.embedding:
        return deserialize_embedding(file_record.embedding)

    file_text = build_file_text(file_record)

    if not file_text.strip():
        return None

    return generate_embedding(file_text)

def classify_with_semantics(file_record, min_score: float = 0.45) -> tuple[str, float, str]:
    file_embedding = get_file_embedding(file_record)

    if file_embedding is None:
        return ("Review", 0.30, "No text available for semantic matching")
    
    best_category = "Review"
    best_score = 0.0

    for category in CATEGORY_DESCRIPTIONS:
        category_embedding = get_category_embedding(category)
        score = cosine_similarity(file_embedding, category_embedding)

        if score > best_score:
            best_category = category
            best_score = score
    
    if best_score >= min_score:
        return (
            best_category,
            best_score,
            f"Matched {best_category} using semantic similarity"
        )
    return ("Review", 0.30, "No strong rule or semantic match")