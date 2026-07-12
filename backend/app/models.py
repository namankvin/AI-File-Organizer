from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base

class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key = True, index = True)
    path = Column(String, unique = True, nullable = False, index = True)
    name = Column(String, nullable = False)
    extension = Column(String, nullable = True, index = True)
    size_bytes = Column(Integer, nullable = False)
    modified_at = Column(DateTime, nullable = False)
    content_hash = Column(String, nullable = True, index = True)
    text_preview = Column(Text, nullable = True)
    embedding = Column(Text, nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default = func.now(), nullable = False)
    updated_at = Column(DateTime, server_default = func.now(), onupdate = func.now(), nullable = False)

class MoveSuggestion(Base): # Proposed action
    __tablename__ = "move_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, nullable=False, index=True)
    source_path = Column(String, nullable=False)
    target_path = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    # Suggestions start as pending and will be applied or dismissed later.
    status = Column(String, nullable=False, index=True, default="pending")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class FileOperation(Base): # Action that actually happened + Stores applied moves so they can be undone later.
    __tablename__ = "file_operations"

    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, nullable=False, index=True)
    file_id = Column(Integer, nullable=False, index=True)
    original_path = Column(String, nullable=False)
    new_path = Column(String, nullable=False)
    operation_type = Column(String, nullable=False, default="move")
    status = Column(String, nullable=False, index=True, default="applied")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    undone_at = Column(DateTime, nullable=True)