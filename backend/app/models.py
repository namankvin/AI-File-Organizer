from sqlalchemy import Column, DateTime, Integer, String, Text
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
    created_at = Column(DateTime, server_default = func.now(), nullable = False)
    updated_at = Column(DateTime, server_default = func.now(), onupdate = func.now(), nullable = False)