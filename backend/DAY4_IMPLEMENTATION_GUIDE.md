# Day 4: Safe Apply, History, and Undo

This guide explains the Day 4 implementation, why each part exists, and how data moves through the application.

## Goal and safety rule

Day 3 creates `MoveSuggestion` rows, but suggestions are only proposals. Day 4 lets the user explicitly approve selected suggestion IDs. The backend then moves only those files, records what happened, and supports undo.

The central rule remains: **a plan never moves a file; only an explicit `/apply` request does.**

## Files changed

- `app/file_actions.py`: validates paths, avoids overwrites, and performs a physical move.
- `app/models.py`: adds `FileOperation`, the permanent history needed for undo.
- `app/schemas.py`: defines and validates the JSON accepted by `/apply`.
- `app/main.py`: adds apply, history, and undo endpoints.
- `tests/test_file_actions.py`: tests filesystem safety in temporary directories.
- `tests/test_apply_undo.py`: tests the database and filesystem data flow together.

## Imports and libraries

### `pathlib.Path`

`Path` represents filesystem paths as objects. It provides readable operations such as `.exists()`, `.is_file()`, `.parent`, and `.name`. Resolving a path also prevents `..` segments or symbolic links from bypassing the allowed-root check.

### `shutil`

`shutil` is part of Python's standard library. `shutil.move()` performs the actual file move and works across directories and filesystems.

### Pydantic: `BaseModel` and `Field`

FastAPI uses Pydantic to validate incoming JSON. `ApplyRequest` requires `suggestion_ids` to be a non-empty list of integers. Invalid JSON is rejected before the endpoint performs any work.

### SQLAlchemy

SQLAlchemy maps Python model objects to SQLite rows. `SessionLocal()` opens a database session. Queries load tracked objects; changing their attributes schedules SQL updates. `db.add()` schedules an insert, `db.commit()` makes changes permanent, and `db.rollback()` discards uncommitted database changes.

### FastAPI `HTTPException`

Raising `HTTPException` stops the endpoint and returns a controlled HTTP error. This implementation uses:

- `400` when a filesystem request is invalid.
- `404` when an operation, suggestion, or file record does not exist.
- `409` when undo conflicts with current state, such as an already-undone operation or an occupied original path.
- `422` automatically when Pydantic rejects the request body.

## Database roles

`FileRecord` is the organizer's current memory of a file. Its path must change whenever the physical file moves.

`MoveSuggestion` is a proposal. Its status begins as `pending`, becomes `applied` after execution, and becomes `undone` if the associated operation is reversed.

`FileOperation` is an audit/history row describing something that actually happened. It stores both `original_path` and `new_path`, which is what makes undo possible.

## Apply data flow

1. A client sends `POST /apply` with JSON such as `{"suggestion_ids": [1, 3]}`.
2. Pydantic creates an `ApplyRequest` and ensures the list is non-empty and contains integers.
3. SQLAlchemy retrieves only matching suggestions whose status is `pending`.
4. The endpoint compares requested IDs with retrieved IDs. Missing or non-pending IDs reject the whole request.
5. The endpoint retrieves every associated `FileRecord` before moving anything. This avoids starting with inconsistent database references.
6. `move_file()` validates the source and destination against `ALLOWED_ROOTS`, creates a collision-free target name, creates the target directory, and calls `shutil.move()`.
7. The endpoint creates a `FileOperation`, marks the suggestion `applied`, and updates the `FileRecord.path` and `.name` to match the actual destination.
8. `db.commit()` makes all database changes permanent.
9. The response reports the original and final paths.

Collision handling matters because the requested target may already exist. If `notes.txt` exists, the actual path becomes `notes (1).txt`; the operation and file record must store that actual returned path.

## Apply failure handling

`db.rollback()` reverses uncommitted database work, but it cannot reverse a physical file move. Therefore the endpoint tracks completed physical moves. If a later move fails, it walks that list backwards and restores earlier files before returning the error.

This is compensation logic: SQLite and the filesystem cannot share one true transaction, so the application explicitly compensates for partially completed filesystem work.

## Undo data flow

1. A client sends `POST /undo/{operation_id}`.
2. The endpoint retrieves the `FileOperation` and requires its status to be `applied`.
3. It retrieves the associated `FileRecord`.
4. It refuses undo if the original path is now occupied, because undo must never overwrite a file.
5. `move_file()` moves `new_path` back to `original_path`.
6. The file record is updated to the restored path.
7. The operation becomes `undone` and receives `undone_at`.
8. The associated suggestion becomes `undone`.
9. The database transaction is committed.

A second undo returns `409 Conflict` because the operation exists but its current state does not permit another undo.

## Read endpoints

`GET /suggestions` returns suggestion previews and statuses. An optional query such as `/suggestions?status=pending` filters the results.

`GET /operations` returns the applied/undone history needed by the future UI.

These use `GET` because they only read state. Apply and undo use `POST` because they change filesystem and database state.

## Rescan and stale embeddings

An embedding represents the filename and extracted content at the time it was generated. When `/scan` detects a changed content hash, it now clears the stored embedding fields. The next `/embed` call regenerates a trustworthy vector instead of semantic search using stale content.

## Running the tests

From `backend` with the virtual environment active:

```bash
pytest -q
```

The tests replace `ALLOWED_ROOTS` with pytest's temporary directory and replace `SessionLocal` with a temporary SQLite database. They never move real sample files or write to `organizer.db`.

## Terminal API checks

Start the server from `backend`:

```bash
uvicorn app.main:app --reload
```

In another terminal, list pending suggestions:

```bash
curl -s "http://127.0.0.1:8000/suggestions?status=pending" | python -m json.tool
```

Apply one selected suggestion:

```bash
curl -s -X POST "http://127.0.0.1:8000/apply" -H "Content-Type: application/json" -d '{"suggestion_ids":[1]}' | python -m json.tool
```

View operation history:

```bash
curl -s "http://127.0.0.1:8000/operations" | python -m json.tool
```

Undo operation 1:

```bash
curl -s -X POST "http://127.0.0.1:8000/undo/1" | python -m json.tool
```

Use IDs returned by your own database; suggestion IDs and operation IDs are not necessarily the same.
