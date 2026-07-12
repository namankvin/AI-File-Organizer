from datetime import datetime
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import file_actions, main
from app.database import Base
from app.models import FileOperation, FileRecord, MoveSuggestion
from app.schemas import ApplyRequest


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", testing_session)
    monkeypatch.setattr(file_actions, "ALLOWED_ROOTS", [tmp_path.resolve()])
    yield testing_session, tmp_path
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def add_pending_move(session_factory, source: Path, target: Path):
    source.write_text("finance", encoding="utf-8")
    db = session_factory()
    file_record = FileRecord(
        path=str(source),
        name=source.name,
        extension=source.suffix,
        size_bytes=source.stat().st_size,
        modified_at=datetime.now(),
    )
    db.add(file_record)
    db.flush()
    suggestion = MoveSuggestion(
        file_id=file_record.id,
        source_path=str(source),
        target_path=str(target),
        category="Finance",
        confidence=0.9,
        reason="Test suggestion",
    )
    db.add(suggestion)
    db.commit()
    ids = (file_record.id, suggestion.id)
    db.close()
    return ids


def test_apply_updates_disk_database_and_history(isolated_app):
    session_factory, root = isolated_app
    source = root / "invoice.txt"
    target = root / "Finance" / "invoice.txt"
    file_id, suggestion_id = add_pending_move(session_factory, source, target)

    response = main.apply_suggestions(ApplyRequest(suggestion_ids=[suggestion_id]))

    assert response["applied_count"] == 1
    assert target.exists()
    assert not source.exists()
    db = session_factory()
    assert db.get(FileRecord, file_id).path == str(target)
    assert db.get(MoveSuggestion, suggestion_id).status == "applied"
    operation = db.query(FileOperation).one()
    assert operation.original_path == str(source)
    assert operation.new_path == str(target)
    db.close()


def test_undo_restores_file_and_rejects_second_undo(isolated_app):
    session_factory, root = isolated_app
    source = root / "invoice.txt"
    target = root / "Finance" / "invoice.txt"
    file_id, suggestion_id = add_pending_move(session_factory, source, target)
    main.apply_suggestions(ApplyRequest(suggestion_ids=[suggestion_id]))
    db = session_factory()
    operation_id = db.query(FileOperation).one().id
    db.close()

    response = main.undo_operation(operation_id)

    assert response["status"] == "undone"
    assert source.exists()
    assert not target.exists()
    db = session_factory()
    assert db.get(FileRecord, file_id).path == str(source)
    assert db.get(FileOperation, operation_id).status == "undone"
    db.close()

    with pytest.raises(HTTPException) as error:
        main.undo_operation(operation_id)
    assert error.value.status_code == 409


def test_apply_rejects_unknown_suggestion(isolated_app):
    with pytest.raises(HTTPException) as error:
        main.apply_suggestions(ApplyRequest(suggestion_ids=[999]))
    assert error.value.status_code == 404
