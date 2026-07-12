from pathlib import Path

import pytest

from app import file_actions


def test_move_file_moves_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(file_actions, "ALLOWED_ROOTS", [tmp_path.resolve()])
    source = tmp_path / "source" / "notes.txt"
    target = tmp_path / "destination" / "notes.txt"
    source.parent.mkdir()
    source.write_text("operating systems", encoding="utf-8")

    final_path = Path(file_actions.move_file(str(source), str(target)))

    assert final_path == target
    assert target.read_text(encoding="utf-8") == "operating systems"
    assert not source.exists()


def test_move_file_avoids_overwriting_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(file_actions, "ALLOWED_ROOTS", [tmp_path.resolve()])
    source = tmp_path / "source.txt"
    target = tmp_path / "notes.txt"
    source.write_text("new", encoding="utf-8")
    target.write_text("old", encoding="utf-8")

    final_path = Path(file_actions.move_file(str(source), str(target)))

    assert final_path.name == "notes (1).txt"
    assert target.read_text(encoding="utf-8") == "old"
    assert final_path.read_text(encoding="utf-8") == "new"


def test_move_file_rejects_path_outside_allowed_root(tmp_path, monkeypatch):
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    source = allowed_root / "notes.txt"
    source.write_text("notes", encoding="utf-8")
    monkeypatch.setattr(file_actions, "ALLOWED_ROOTS", [allowed_root.resolve()])

    with pytest.raises(ValueError, match="Target path is outside allowed roots"):
        file_actions.move_file(str(source), str(tmp_path / "outside.txt"))


def test_move_file_rejects_missing_source(tmp_path, monkeypatch):
    monkeypatch.setattr(file_actions, "ALLOWED_ROOTS", [tmp_path.resolve()])

    with pytest.raises(FileNotFoundError, match="Source file does not exist"):
        file_actions.move_file(str(tmp_path / "missing.txt"), str(tmp_path / "target.txt"))
