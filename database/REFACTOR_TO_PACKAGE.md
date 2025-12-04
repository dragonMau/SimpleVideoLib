Goal
=====
Move the current database service (currently in `services/database.py`) into a standalone package folder `database/` so it can be tested and imported as a library. Make small, well-scoped changes to support both running as a script and importing for tests (including using an in-memory SQLite DB for unit tests). Also improve `print_db` so it prints the actual SQL tables (not pseudo-relationships) in a fixed-width table layout.

Design goals
============
- Keep behavior identical to current app unless explicitly changed.
- Make minimal API changes to support tests: allow injecting DB path/URI instead of hard-coded config constant.
- Expose a clean package surface via `database.__init__` so other modules can `from database import DataBaseManager, DBVideo, DBPlaylist, DBGroup`.
- Provide a test helper that can run against `:memory:` or a temporary file DB.
- Replace `print_db` with a deterministic function that shows exactly what SQL contains with aligned columns.

High-level steps
================
1. Create package folder `database/` and add `__init__.py`.
2. Move `services/database.py` -> `database/__init__.py` (or split into modules inside package if desired).
3. Change `DataBaseManager` to accept optional `db_path` and `db_uri` parameters (default to current `config.DB_PATH, DB_URI`). Use instance attributes rather than globals inside methods.
4. Update all internal uses of the old global `DB_PATH`/`DB_URI` to use the instance attributes (e.g., `self.db_path`) so tests can instantiate `DataBaseManager(db_path=':memory:')`.
5. Implement `database.print_db` as described below and replace prior implementation.
6. Add `tests/test_database.py` with small unit tests using `pytest`, running with `DataBaseManager(db_path=':memory:', db_uri=False)`.
7. Update imports in the rest of the codebase to `from database import DataBaseManager` (or keep `services` wrapper that imports from `database` to avoid changing many files immediately).

Detailed file layout suggestion
==============================
(database/) package root
- __init__.py          # exports DataBaseManager, DBVideo, DBPlaylist, DBGroup
- manager.py           # DataBaseManager class and utilities (init_db, print_db, etc.)
- models.py            # DBItem, DBVideo, DBPlaylist, DBGroup classes
- exceptions.py        # re-export of database_exceptions or small wrappers
- tests/
  - test_database.py   # pytest tests that import the package and run operations

This split is optional; you may simply move the current `services/database.py` content into `database/__init__.py` and apply the changes described below.

Minimal API changes required
===========================
- DataBaseManager.__init__(self, db_path=None, db_uri=None)
  - If db_path/db_uri are None, fall back to config.DB_PATH and config.DB_URI
  - Store as self.db_path and self.db_uri
- Update the `connected` decorator to use the instance's path: it must be defined so that the wrapper gets `self` and opens `sqlite3.connect(self.db_path, uri=self.db_uri)`.
  - Example: define connected as an instance-decorator factory (code provided below).

Important: how to keep compatibility with existing code
======================================================
- To avoid changing many files at once, create `services/database.py` that simply imports the public symbols from `database`:

```py
# services/database.py
from database import DataBaseManager, DBVideo, DBPlaylist, DBGroup
__all__ = ['DataBaseManager', 'DBVideo', 'DBPlaylist', 'DBGroup']
```

This keeps existing imports working while moving implementation into the package.

Example code snippets
=====================
1) connected decorator that uses instance DB path (put into `manager.py` near DataBaseManager):

```py
import functools, sqlite3

def connected(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # self must be DataBaseManager instance
        with sqlite3.connect(self.db_path, uri=self.db_uri) as conn:
            cursor = conn.cursor()
            return func(self, *args, cursor=cursor, **kwargs)
    return wrapper
```

2) DataBaseManager.__init__ signature and defaults:

```py
class DataBaseManager:
    def __init__(self, db_path=None, db_uri=None):
        from config import DB_PATH as DEFAULT_DB_PATH, DB_URI as DEFAULT_DB_URI
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self.db_uri = db_uri if db_uri is not None else DEFAULT_DB_URI
        self.log_level = 1
```

4) Example `database/__init__.py` minimal exports

```py
from .manager import DataBaseManager
from .models import DBVideo, DBPlaylist, DBGroup

__all__ = ['DataBaseManager', 'DBVideo', 'DBPlaylist', 'DBGroup']
```

5) Make `DataBaseManager.init_db()` idempotent and safe to call in tests. Already in code it uses CREATE TABLE IF NOT EXISTS — keep that.

Testing guidance
===============
- Use pytest and an in-memory SQLite DB for fast tests.
- Example test file `tests/test_database.py`:

```py
import tempfile
from database import DataBaseManager, DBVideo, DBPlaylist

def test_create_and_link():
    db = DataBaseManager(db_path=':memory:', db_uri=False)
    db.init_db()

    pl = db.create_playlist('t1')
    v = DBVideo.create(db, 'archive-1')
    v.title = 'X'
    v.playlists_ids.append(pl)
    v.save()

    # reload and assert
    v2 = DBVideo(v.id_)
    assert pl in v2.playlists_ids
```

- Running tests (PowerShell):

```powershell
# from repo root
python -m pip install -U pytest
pytest -q
```

Migration checklist for code changes
===================================
- [ ] Move file contents to `database/` package and create `__init__.py` as above (or split manager/models).
- [ ] Update the `connected` decorator to use `self.db_path/self.db_uri` or turn it into an instance method decorator factory.
- [ ] Provide a thin `services/database.py` shim that re-exports new package names so other modules don't need immediate edits.
- [ ] Run tests (or `python database` if you keep demo section in `__main__`) and iterate until green.

Small recommended code cleanups
==============================
- Make `DataBaseManager.create_*` methods `@connected` instance methods and keep them returning ids.
- Avoid module-level `DB_PATH` usage; instead rely on instance attributes.
- Ensure classes `DBVideo`, `DBPlaylist`, `DBGroup` accept a `DataBaseManager` instance as needed or else use the `connected` decorator that obtains a cursor from the manager instance.

Example: update DBVideo.create to take `dbman` argument (current code already does this) — when moving to package, keep that pattern. For tests, create a DataBaseManager instance with `db_path=':memory:'` and pass it through.

What I can do next
==================
- I can create the `database/` package and move the current `services/database.py` contents into `database/` and add a `services/database.py` shim that re-exports. This will update imports across the project if you want.
- I can implement the `print_db` change directly in the code for you now and run the demo/tests.

Tell me which of the next steps you want me to take and I'll perform them.
